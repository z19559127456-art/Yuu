import { useSyncExternalStore } from 'react';
import zh from './zh-CN';
import en from './en-US';

type Locale = 'zh-CN' | 'en-US';
type Translations = Record<string, string>;

const locales: Record<Locale, Translations> = { 'zh-CN': zh, 'en-US': en };

let currentLocale: Locale = 'zh-CN';
let listeners: Array<() => void> = [];

function subscribe(cb: () => void) {
  listeners.push(cb);
  return () => {
    listeners = listeners.filter((l) => l !== cb);
  };
}

function notify() {
  listeners.forEach((l) => l());
}

export function setLocale(locale: Locale) {
  if (locale === currentLocale) return;
  currentLocale = locale;
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('locale', locale);
  }
  notify();
}

export function getLocale(): Locale {
  return currentLocale;
}

export function t(key: string, params?: Record<string, string | number>): string {
  const translations = locales[currentLocale];
  let text = translations[key];
  if (text === undefined) {
    text = locales['zh-CN'][key] ?? key;
  }
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replace(`{${k}}`, String(v));
    }
  }
  return text;
}

export function useT() {
  useSyncExternalStore(subscribe, () => currentLocale);
  return { t, setLocale, locale: currentLocale };
}

// Initialize from localStorage
if (typeof localStorage !== 'undefined') {
  const saved = localStorage.getItem('locale') as Locale | null;
  if (saved && locales[saved]) {
    currentLocale = saved;
  }
}
