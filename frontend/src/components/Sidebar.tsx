import { useStore } from '@/store/useStore';
import { MessageSquare, Users, Settings } from 'lucide-react';
import type { NavItem } from '@/types';

const navItems: { key: NavItem; icon: typeof MessageSquare; label: string }[] = [
  { key: 'chats', icon: MessageSquare, label: '消息' },
  { key: 'contacts', icon: Users, label: '通讯录' },
  { key: 'settings', icon: Settings, label: '设置' },
];

export default function Sidebar() {
  const activeNav = useStore((s) => s.activeNav);
  const setActiveNav = useStore((s) => s.setActiveNav);

  return (
    <nav className="w-16 bg-gray-900 flex flex-col items-center py-4 gap-2 flex-shrink-0">
      {navItems.map(({ key, icon: Icon, label }) => {
        const isActive = activeNav === key;
        return (
          <button
            key={key}
            onClick={() => setActiveNav(key)}
            className={`relative flex flex-col items-center justify-center w-12 h-12 rounded-lg transition-colors
              ${isActive ? 'text-green-400' : 'text-gray-400 hover:text-gray-200'}`}
            title={label}
          >
            {isActive && (
              <span className="absolute left-[-8px] top-1/2 -translate-y-1/2 w-1 h-6 bg-green-400 rounded-r" />
            )}
            <Icon className="w-5 h-5" />
            <span className="text-[10px] mt-0.5">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
