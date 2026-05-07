import { describe, it, expect } from 'vitest';
import { render } from './test-utils';
import MessageBubble from '@/components/MessageBubble';
import type { Message } from '@/types';

function makeMsg(overrides: Partial<Message> = {}): Message {
  return {
    id: 'm1',
    conversation_id: 'c1',
    role: 'user',
    type: 'text',
    content: '',
    attachments: [],
    tool_calls: [],
    tool_results: [],
    reply_to: '',
    is_edited: false,
    edited_from: '',
    is_pinned: false,
    is_remembered: false,
    status: 'sent',
    created_at: '2026-05-07T10:00:00Z',
    updated_at: '2026-05-07T10:00:00Z',
    ...overrides,
  };
}

describe('MessageBubble', () => {
  it('renders user message', () => {
    const msg = makeMsg({ role: 'user', content: '你好' });
    const { container } = render(<MessageBubble message={msg} />);
    expect(container.textContent).toContain('你好');
    expect(container.textContent).toContain('我');
  });

  it('renders assistant message', () => {
    const msg = makeMsg({ role: 'assistant', content: '你好！' });
    const { container } = render(<MessageBubble message={msg} />);
    expect(container.textContent).toContain('你好！');
    expect(container.textContent).toContain('AI');
  });

  it('renders system message as centered notice', () => {
    const msg = makeMsg({ role: 'system', content: '系统通知' });
    const { container } = render(<MessageBubble message={msg} />);
    const span = container.querySelector('.text-gray-400');
    expect(span).toBeTruthy();
    expect(container.textContent).toContain('系统通知');
  });

  it('shows typing indicator when streaming with empty content', () => {
    const msg = makeMsg({ role: 'assistant', content: '', status: 'sending' });
    const { container } = render(<MessageBubble message={msg} />);
    // Should contain animated dots
    const dots = container.querySelectorAll('.animate-bounce');
    expect(dots.length).toBe(3);
  });

  it('shows recalled message indicator', () => {
    const msg = makeMsg({ role: 'assistant', content: 'secret', status: 'cancelled' });
    const { container } = render(<MessageBubble message={msg} />);
    expect(container.textContent).toContain('消息已撤回');
  });

  it('shows failed status indicator', () => {
    const msg = makeMsg({ role: 'assistant', content: 'hello', status: 'failed' });
    const { container } = render(<MessageBubble message={msg} />);
    expect(container.textContent).toContain('发送失败');
  });

  it('shows edited indicator', () => {
    const msg = makeMsg({ role: 'user', content: 'hello', is_edited: true });
    const { container } = render(<MessageBubble message={msg} />);
    expect(container.textContent).toContain('已编辑');
  });
});
