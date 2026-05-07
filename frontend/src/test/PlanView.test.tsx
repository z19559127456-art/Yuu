import { describe, it, expect } from 'vitest';
import { render, fireEvent } from './test-utils';
import PlanView from '@/components/PlanView';

function makePlan(overrides = {}) {
  return {
    id: 'p1',
    title: '测试计划',
    description: '这是一个测试计划',
    status: 'running' as const,
    subtasks: [
      { id: 's1', title: '前置任务', description: '第一步', status: 'completed' as const, depends_on: [], order_index: 0 },
      { id: 's2', title: '后置任务', description: '第二步', status: 'pending' as const, depends_on: ['0'], order_index: 1 },
      { id: 's3', title: '独立任务', status: 'running' as const, order_index: 2 },
    ],
    created_at: '2026-05-07T10:00:00Z',
    updated_at: '2026-05-07T10:30:00Z',
    ...overrides,
  };
}

describe('PlanView', () => {
  it('renders plan title and status', () => {
    const { container } = render(<PlanView plan={makePlan()} />);
    expect(container.textContent).toContain('测试计划');
    expect(container.textContent).toContain('running');
  });

  it('renders subtask count', () => {
    const { container } = render(<PlanView plan={makePlan()} />);
    expect(container.textContent).toContain('1/3');
    expect(container.textContent).toContain('子任务');
  });

  it('renders subtask titles', () => {
    const { container } = render(<PlanView plan={makePlan()} />);
    expect(container.textContent).toContain('前置任务');
    expect(container.textContent).toContain('后置任务');
    expect(container.textContent).toContain('独立任务');
  });

  it('shows description in header', () => {
    const { container } = render(<PlanView plan={makePlan()} />);
    expect(container.textContent).toContain('这是一个测试计划');
  });

  it('collapses when header clicked', () => {
    const { container } = render(<PlanView plan={makePlan()} />);
    const button = container.querySelector('button');
    expect(button).toBeTruthy();
    if (button) {
      // Initially not collapsed — subtasks visible
      expect(container.textContent).toContain('前置任务');
      fireEvent.click(button);
      // After collapse — subtasks hidden
      expect(container.textContent).not.toContain('前置任务');
    }
  });

  it('shows empty state for plans with no subtasks', () => {
    const plan = makePlan({ subtasks: [] });
    const { container } = render(<PlanView plan={plan} />);
    expect(container.textContent).toContain('暂无数据');
  });
});
