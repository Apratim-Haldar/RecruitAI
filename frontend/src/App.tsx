import { Routes, Route, BrowserRouter as Router } from "react-router-dom";
import Landing from "./pages/Landing";
import Hr from "./pages/Hr";
import JobDetails from "./pages/JobDetails";
import ProtectedRoute from "./components/protected-route";
import { CookiesProvider } from "react-cookie";
function App() {
  return (
    <CookiesProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route
            path="/hr"
            element={
              <ProtectedRoute>
                <Hr />
              </ProtectedRoute>
            }
          />
          <Route path="/jobs/:jobId" element={<JobDetails />} />
        </Routes>
      </Router>
    </CookiesProvider>
  );
}

export default App;
