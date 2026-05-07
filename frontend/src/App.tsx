import { useWebSocket } from '@/hooks/useWebSocket';
import Layout from '@/components/Layout';

function App() {
  const { sendJson } = useWebSocket();

  return <Layout sendJson={sendJson} />;
}

export default App;
