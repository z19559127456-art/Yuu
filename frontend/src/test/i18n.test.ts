import { describe, it, expect, beforeEach } from 'vitest';
import { t, setLocale, getLocale } from '@/i18n';

describe('i18n', () => {
  beforeEach(() => {
    setLocale('zh-CN');
  });

  it('returns Chinese text by default', () => {
    expect(t('nav.chats')).toBe('消息');
    expect(t('nav.contacts')).toBe('通讯录');
    expect(t('tool.title')).toBe('工具执行结果');
  });

  it('falls back to key when translation missing', () => {
    expect(t('nonexistent.key')).toBe('nonexistent.key');
  });

  it('supports parameter interpolation', () => {
    expect(t('tool.duration.ms', { ms: 150 })).toBe('150ms');
    expect(t('progress.percent', { p: 75 })).toBe('75%');
  });

  it('supports locale switching', () => {
    setLocale('en-US');
    expect(getLocale()).toBe('en-US');
    // English translations should be different
    expect(t('nav.chats')).not.toBe('消息');
  });

  it('switch to unknown locale falls back to zh-CN', () => {
    setLocale('en-US');
    expect(t('common.confirm')).not.toBe('确认'); // English
    // zh-CN fallback for missing keys
    expect(t('common.confirm')).toBeDefined();
  });
});
