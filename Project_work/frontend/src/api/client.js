import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function solveTransportation(payload) {
  const { data } = await api.post('/transportation/solve', payload)
  return data
}

export async function explainTransportation(payload) {
  const { data } = await api.post('/transportation/explain', payload)
  return data
}

export async function solveAssignment(payload) {
  const { data } = await api.post('/assignment/solve', payload)
  return data
}

export async function explainAssignment(payload) {
  const { data } = await api.post('/assignment/explain', payload)
  return data
}

export async function getTransportationHistory() {
  const { data } = await api.get('/history/transportation')
  return data
}

export async function getAssignmentHistory() {
  const { data } = await api.get('/history/assignment')
  return data
}

export async function deleteTransportationProblem(id) {
  const { data } = await api.delete(`/history/transportation/${id}`)
  return data
}

export async function deleteAssignmentProblem(id) {
  const { data } = await api.delete(`/history/assignment/${id}`)
  return data
}

export async function getTransportationDetails(id) {
  const { data } = await api.get(`/history/transportation/${id}/details`)
  return data
}

export async function getAssignmentDetails(id) {
  const { data } = await api.get(`/history/assignment/${id}/details`)
  return data
}

export default api
