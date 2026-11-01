import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import Transportation from './pages/Transportation.jsx'
import Assignment from './pages/Assignment.jsx'
import Saved from './pages/Saved.jsx'
import Help from './pages/Help.jsx'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="/transportation" element={<Transportation />} />
          <Route path="/assignment" element={<Assignment />} />
          <Route path="/saved" element={<Saved />} />
          <Route path="/help" element={<Help />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
