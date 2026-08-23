import { TelegramBotClient } from "./telegram.ts";
import type { TelegramBotCommand } from "./types.ts";

export const CHINESE_BOT_COMMANDS: TelegramBotCommand[] = [
  { command: "start", description: "NVIDIA 免费模型监控" },
  { command: "models", description: "浏览免费模型目录" },
  { command: "model", description: "查询指定模型" },
  { command: "help", description: "查看使用帮助" },
];

export const ENGLISH_BOT_COMMANDS: TelegramBotCommand[] = [
  { command: "start", description: "NVIDIA Free Endpoint Monitor" },
  { command: "models", description: "Browse free model catalog" },
  { command: "model", description: "Query specific model details" },
  { command: "help", description: "Usage guide and help" },
];

export interface MenuInjectionResult {
  success: boolean;
  registeredScopes: string[];
  errors: string[];
}

export async function injectBotCommands(botClient: TelegramBotClient): Promise<MenuInjectionResult> {
  const result: MenuInjectionResult = {
    success: true,
    registeredScopes: [],
    errors: [],
  };

  const targets = [
    // 1. Default scope (Chinese fallback)
    { scope: { type: "default" as const }, lang: undefined, commands: CHINESE_BOT_COMMANDS, label: "default (zh-default)" },
    // 2. Default scope (Chinese explicit)
    { scope: { type: "default" as const }, lang: "zh", commands: CHINESE_BOT_COMMANDS, label: "default (zh)" },
    // 3. Default scope (English explicit)
    { scope: { type: "default" as const }, lang: "en", commands: ENGLISH_BOT_COMMANDS, label: "default (en)" },
    // 4. All Private Chats scope (Chinese)
    { scope: { type: "all_private_chats" as const }, lang: undefined, commands: CHINESE_BOT_COMMANDS, label: "all_private_chats (zh-default)" },
    { scope: { type: "all_private_chats" as const }, lang: "zh", commands: CHINESE_BOT_COMMANDS, label: "all_private_chats (zh)" },
    // 5. All Private Chats scope (English)
    { scope: { type: "all_private_chats" as const }, lang: "en", commands: ENGLISH_BOT_COMMANDS, label: "all_private_chats (en)" },
  ];

  for (const target of targets) {
    try {
      await botClient.setMyCommands(target.commands, {
        scope: target.scope,
        language_code: target.lang,
      });
      result.registeredScopes.push(target.label);
    } catch (err) {
      result.success = false;
      result.errors.push(`Failed to register ${target.label}: ${(err as Error).message}`);
    }
  }

  return result;
}
