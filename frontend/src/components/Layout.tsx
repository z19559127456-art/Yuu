import { useStore } from '@/store/useStore';
import type { WSClientMessage } from '@/types';
import Sidebar from './Sidebar';
import AgentList from './AgentList';
import ContactsView from './ContactsView';
import SettingsView from './SettingsView';
import ChatArea from './ChatArea';
import AgentCreatePanel from './AgentCreatePanel';
import ApprovalDialog from './ApprovalDialog';

interface Props {
  sendJson: (msg: WSClientMessage) => void;
}

export default function Layout({ sendJson }: Props) {
  const activeNav = useStore((s) => s.activeNav);
  const pendingApproval = useStore((s) => s.pendingApproval);
  const setPendingApproval = useStore((s) => s.setPendingApproval);

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

      {pendingApproval && (
        <ApprovalDialog
          requestId={pendingApproval.request_id}
          type={pendingApproval.approval_type}
          context={pendingApproval.context}
          requester={pendingApproval.requester}
          timeoutSeconds={pendingApproval.timeout_seconds}
          dangerous={pendingApproval.dangerous}
          onRespond={(requestId, response, feedback, modifiedParams) => {
            sendJson({
              type: 'approval_response',
              request_id: requestId,
              response,
              feedback,
              modified_params: modifiedParams,
            });
            setPendingApproval(null);
          }}
        />
      )}
    </div>
  );
}
