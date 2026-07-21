import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ScamDetection from './pages/ScamDetection'
import Counterfeit from './pages/Counterfeit'
import FraudGraph from './pages/FraudGraph'
import Geospatial from './pages/Geospatial'
import CitizenShield from './pages/CitizenShield'
import AuditLog from './pages/AuditLog'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard"      element={<Dashboard />} />
          <Route path="/scam-detection" element={<ScamDetection />} />
          <Route path="/counterfeit"    element={<Counterfeit />} />
          <Route path="/fraud-graph"    element={<FraudGraph />} />
          <Route path="/geospatial"     element={<Geospatial />} />
          <Route path="/citizen-shield" element={<CitizenShield />} />
          <Route path="/audit"          element={<AuditLog />} />
          <Route path="*"              element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
