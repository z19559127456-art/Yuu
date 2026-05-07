import { useStore } from '@/store/useStore';
import type { WSClientMessage } from '@/types';
import Sidebar from './Sidebar';
import AgentList from './AgentList';
import ContactsView from './ContactsView';
import SettingsView from './SettingsView';
import ChatArea from './ChatArea';
import AgentCreatePanel from './AgentCreatePanel';

interface Props {
  sendJson: (msg: WSClientMessage) => void;
}

export default function Layout({ sendJson }: Props) {
  const activeNav = useStore((s) => s.activeNav);

  const leftPanel = () => {
    switch (activeNav) {
      case 'contacts':
        return <ContactsView sendJson={sendJson} />;
      case 'settings':
        return <SettingsView />;
      default:
        return <AgentList />;
    }
  };

  return (
    <div className="h-screen flex overflow-hidden bg-white">
      <Sidebar />
      {leftPanel()}
      <ChatArea sendJson={sendJson} />
      <AgentCreatePanel sendJson={sendJson} />
    </div>
  );
}
