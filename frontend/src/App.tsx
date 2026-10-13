import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Login from "@/pages/Login";
import Callback from "@/pages/Callback";
import GrillSession from "@/pages/GrillSession";
import PrdView from "@/pages/PrdView";
import IssueBoard from "@/pages/IssueBoard";
import Verification from "@/pages/Verification";
import Settings from "@/pages/Settings";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="page flex items-center justify-center">
        <div className="empty-state">
          <div className="empty-state-icon">⏳</div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function App() {
  const { loading } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={loading ? null : <Login />} />
      <Route path="/callback" element={<Callback />} />
      <Route
        path="/*"
        element={
          <PrivateRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/session/:sessionId/grill" element={<GrillSession />} />
                <Route path="/session/:sessionId/prd/:prdId?" element={<PrdView />} />
                <Route path="/session/:sessionId/issues" element={<IssueBoard />} />
                <Route path="/session/:sessionId/verification" element={<Verification />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Layout>
          </PrivateRoute>
        }
      />
    </Routes>
  );
}

export default App;