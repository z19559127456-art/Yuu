const zh: Record<string, string> = {
  // Navigation
  'nav.chats': '消息',
  'nav.contacts': '通讯录',
  'nav.settings': '设置',

  // Common
  'common.confirm': '确认',
  'common.cancel': '取消',
  'common.save': '保存',
  'common.delete': '删除',
  'common.edit': '编辑',
  'common.create': '新建',
  'common.search': '搜索',
  'common.loading': '加载中...',
  'common.empty': '暂无数据',
  'common.error': '出错了',
  'common.retry': '重试',
  'common.close': '关闭',

  // Agent
  'agent.create': '创建 Agent',
  'agent.edit': '编辑 Agent',
  'agent.name': '名称',
  'agent.role': '角色',
  'agent.model': '模型',
  'agent.temperature': '温度',
  'agent.system_prompt': '系统提示词',
  'agent.tools': '工具',
  'agent.skills': '技能',
  'agent.active': '已启用',
  'agent.inactive': '已禁用',

  // Tool Output
  'tool.title': '工具执行结果',
  'tool.call': '工具调用',
  'tool.result': '执行结果',
  'tool.status.success': '成功',
  'tool.status.error': '失败',
  'tool.status.running': '执行中',
  'tool.args': '参数',
  'tool.duration': '耗时',
  'tool.duration.ms': '{ms}ms',

  // Plan View
  'plan.title': '任务计划',
  'plan.status.pending': '待执行',
  'plan.status.running': '执行中',
  'plan.status.completed': '已完成',
  'plan.status.failed': '失败',
  'plan.status.cancelled': '已取消',
  'plan.status.skipped': '已跳过',
  'plan.subtask': '子任务',
  'plan.depends_on': '依赖',
  'plan.depth': '层级',
  'plan.create_time': '创建时间',

  // Task Progress
  'progress.title': '任务进度',
  'progress.overall': '总体进度',
  'progress.total': '总计',
  'progress.completed': '已完成',
  'progress.remaining': '剩余',
  'progress.percent': '{p}%',

  // Task History
  'history.title': '任务历史',
  'history.all': '全部',
  'history.success': '成功',
  'history.failed': '失败',
  'history.running': '运行中',
  'history.empty': '暂无任务记录',
  'history.type': '任务类型',
  'history.time': '执行时间',
  'history.duration': '耗时',

  // Group Chat
  'group.title': '群聊',
  'group.create': '创建群聊',
  'group.topic': '讨论主题',
  'group.mode.discussion': '讨论模式',
  'group.mode.task': '任务模式',
  'group.participants': '参与者',
  'group.round': '第 {n} 轮',
  'group.role.moderator': '主持',
  'group.role.participant': '参与',
  'group.role.observer': '观察',
  'group.empty': '暂无群聊会话',
  'group.input_placeholder': '发送消息到群聊...',

  // Free Dialogue
  'free_dialogue.title': '自由对话',
  'free_dialogue.start': '开始自由对话',
  'free_dialogue.stop': '停止对话',
  'free_dialogue.typing': '{name} 正在输入...',
  'free_dialogue.consensus': '达成共识',
  'free_dialogue.dissenting': '异议者',
  'free_dialogue.ended': '对话结束',
  'free_dialogue.turns': '共 {n} 轮',

  // Approval
  'approval.title': '审批确认',
  'approval.tool_execution': '工具执行审批',
  'approval.plan_approval': '计划审批',
  'approval.final_result': '最终结果审批',
  'approval.dangerous_action': '高危操作审批',
  'approval.approve': '批准',
  'approval.reject': '拒绝',
  'approval.modify': '修改',
  'approval.feedback': '添加反馈',
  'approval.timeout': '审批超时，自动拒绝',
  'approval.context': '审批内容',
  'approval.requester': '发起者',

  // Task Dispatch
  'dispatch.decompose': '拆分并派发',
  'dispatch.progress': '任务进度',
  'dispatch.merged': '任务完成',
  'dispatch.retry': '重试子任务',

  // Group mode
  'group.mode.free_dialogue': '自由对话',
  'group.mode_switch': '切换模式',

  // Settings
  'settings.title': '设置',
  'settings.connection': '连接状态',
  'settings.connected': '已连接到后端服务',
  'settings.disconnected': '未连接',
  'settings.theme': '主题',
  'settings.light': '浅色',
  'settings.dark': '深色',
  'settings.language': '语言',
  'settings.about': '关于',
  'settings.version': '版本',
  'settings.app_name': 'Yu',
  'settings.app_desc': 'AI Agent Messenger OS',
};

export default zh;
