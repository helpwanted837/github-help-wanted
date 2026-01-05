import type { PlatformAdapter } from "./base.js";

const adapters = new Map<string, PlatformAdapter>();

export function registerAdapter(adapter: PlatformAdapter): void {
  if (adapters.has(adapter.name)) {
    throw new Error(`Adapter "${adapter.name}" already registered`);
  }
  adapters.set(adapter.name, adapter);
}

export function getAdapter(name: string): PlatformAdapter | undefined {
  return adapters.get(name);
}

export function getAllAdapters(): PlatformAdapter[] {
  return Array.from(adapters.values());
}

export function getAdapterNames(): string[] {
  return Array.from(adapters.keys());
}
