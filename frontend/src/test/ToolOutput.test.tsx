import { describe, it, expect } from 'vitest';
import { render } from './test-utils';
import ToolOutput from '@/components/ToolOutput';

describe('ToolOutput', () => {
  it('returns null when no tool calls or results', () => {
    const { container } = render(<ToolOutput />);
    expect(container.firstChild).toBeNull();
  });

  it('renders tool calls list', () => {
    const toolCalls = [
      { id: 'tc1', name: 'read_file', arguments: { path: '/test.txt' } },
    ];
    const { container } = render(<ToolOutput toolCalls={toolCalls} />);
    expect(container.textContent).toContain('read_file');
    expect(container.textContent).toContain('工具执行结果');
  });

  it('shows running status for tools without results', () => {
    const toolCalls = [
      { id: 'tc1', name: 'web_search', arguments: { query: 'test' } },
    ];
    const { container } = render(<ToolOutput toolCalls={toolCalls} />);
    expect(container.textContent).toContain('执行中');
  });

  it('shows success status for completed tools', () => {
    const toolCalls = [
      { id: 'tc1', name: 'cli_exec', arguments: { cmd: 'ls' } },
    ];
    const toolResults = [
      { tool_call_id: 'tc1', result: 'file1.txt', status: 'success' as const },
    ];
    const { container } = render(<ToolOutput toolCalls={toolCalls} toolResults={toolResults} />);
    expect(container.textContent).toContain('成功');
  });

  it('shows error status for failed tools', () => {
    const toolCalls = [
      { id: 'tc1', name: 'web_search', arguments: { query: 'test' } },
    ];
    const toolResults = [
      { tool_call_id: 'tc1', result: 'timed out', status: 'error' as const },
    ];
    const { container } = render(<ToolOutput toolCalls={toolCalls} toolResults={toolResults} />);
    expect(container.textContent).toContain('失败');
  });

  it('shows streaming indicator when isStreaming is true', () => {
    const toolCalls = [
      { id: 'tc1', name: 'fetch_url', arguments: { url: 'https://example.com' } },
    ];
    const { container } = render(<ToolOutput toolCalls={toolCalls} isStreaming />);
    // Should have an extra loading spinner for streaming
    const loaders = container.querySelectorAll('.animate-spin');
    expect(loaders.length).toBeGreaterThanOrEqual(1);
  });
});
