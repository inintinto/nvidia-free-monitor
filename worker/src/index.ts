import { CatalogStore } from "./catalog.ts";
import { BUNDLED_BASELINE, BUNDLED_CATALOG, BUNDLED_LIFECYCLE } from "./default_data.ts";
import { GitHubDataLoader } from "./github_client.ts";
import { BotCommandHandler } from "./handlers.ts";
import { injectBotCommands } from "./menu.ts";
import { TelegramBotClient } from "./telegram.ts";
import type { Env, TelegramUpdate } from "./types.ts";

// In-memory global store instance for worker lifespan
let globalStore: CatalogStore | null = null;
let globalDataLoader: GitHubDataLoader | null = null;

async function getOrInitCatalogStore(env: Env): Promise<CatalogStore> {
  if (!globalStore) {
    globalStore = new CatalogStore(
      BUNDLED_CATALOG as { models?: Record<string, Record<string, unknown>> },
      BUNDLED_LIFECYCLE as { history?: Record<string, Record<string, unknown>> },
      BUNDLED_BASELINE as { models?: Array<{ id: string; owned_by?: string }> }
    );
  }

  if (!globalDataLoader) {
    globalDataLoader = new GitHubDataLoader(
      env.GITHUB_REPO || "inintinto/nvidia-free-monitor",
      env.GITHUB_BRANCH || "main",
      5 // 5 minutes cache
    );
  }

  // Attempt to refresh catalog from GitHub Raw
  try {
    const catalogData = await globalDataLoader.getModelCatalog();
    const lifecycleData = await globalDataLoader.getLifecycle();
    const baselineData = await globalDataLoader.getBaseline();
    if (catalogData || lifecycleData || baselineData) {
      globalStore.rebuild(
        catalogData ? { models: catalogData.models as Record<string, Record<string, unknown>> } : undefined,
        lifecycleData ? { history: lifecycleData.history as Record<string, Record<string, unknown>> } : undefined,
        baselineData ? { models: baselineData.models as Array<{ id: string; owned_by?: string }> } : undefined
      );
    }
  } catch {
    // Graceful fallback to existing in-memory store
  }

  return globalStore;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Health check
    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "nvidia-free-monitor-worker",
          version: "3.0.0-stage2b",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Bot Command Menu Injection Endpoint (Protected by INIT_COMMAND_SECRET)
    if (request.method === "POST" && url.pathname === "/telegram/init-commands") {
      // 1. Verify INIT_COMMAND_SECRET header
      if (env.INIT_COMMAND_SECRET) {
        const receivedInitSecret = request.headers.get("X-Init-Command-Secret");
        if (receivedInitSecret !== env.INIT_COMMAND_SECRET) {
          return new Response(
            JSON.stringify({ error: "Unauthorized: Invalid or missing X-Init-Command-Secret header." }),
            { status: 401, headers: { "Content-Type": "application/json" } }
          );
        }
      }

      if (!env.TELEGRAM_BOT_TOKEN) {
        return new Response(
          JSON.stringify({ error: "TELEGRAM_BOT_TOKEN is not configured in Worker Secrets." }),
          { status: 500, headers: { "Content-Type": "application/json" } }
        );
      }

      const botClient = new TelegramBotClient(env.TELEGRAM_BOT_TOKEN);
      const result = await injectBotCommands(botClient);
      return new Response(JSON.stringify(result, null, 2), {
        status: result.success ? 200 : 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Telegram Webhook Handler
    if (request.method === "POST" && (url.pathname === "/telegram/webhook" || url.pathname === "/webhook")) {
      // 1. Verify Webhook Secret Token if configured
      if (env.TELEGRAM_WEBHOOK_SECRET_TOKEN) {
        const receivedSecret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
        if (receivedSecret !== env.TELEGRAM_WEBHOOK_SECRET_TOKEN) {
          return new Response("Unauthorized webhook request", { status: 401 });
        }
      }

      if (!env.TELEGRAM_BOT_TOKEN) {
        return new Response("TELEGRAM_BOT_TOKEN is missing", { status: 500 });
      }

      let update: TelegramUpdate;
      try {
        update = (await request.json()) as TelegramUpdate;
      } catch {
        return new Response("Invalid JSON Update", { status: 400 });
      }

      const botClient = new TelegramBotClient(env.TELEGRAM_BOT_TOKEN);
      const store = await getOrInitCatalogStore(env);
      const handler = new BotCommandHandler(botClient, store);

      // Safe non-blocking execution
      try {
        if (update.message) {
          await handler.handleMessage(update.message);
        } else if (update.callback_query) {
          await handler.handleCallbackQuery(update.callback_query);
        }
      } catch (err) {
        console.error(`[WARN] Error processing update ${update.update_id}: ${(err as Error).message}`);
      }

      // Acknowledge update to Telegram
      return new Response("OK", { status: 200 });
    }

    return new Response("Not Found", { status: 404 });
  },
};
