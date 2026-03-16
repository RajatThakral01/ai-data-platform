import axios from 'axios';
import { 
  UploadResponse, 
  EDAResponse, 
  CleanResponse, 
  MLResponse, 
  InsightsResponse, 
  QueryResponse, 
  StatsResponse, 
  LogEntry 
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const uploadFile = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API_URL}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const runEDA = async (sessionId: string): Promise<EDAResponse> => {
  const response = await axios.post(`${API_URL}/eda`, { session_id: sessionId });
  return response.data;
};

export const runCleaning = async (sessionId: string, autoClean: boolean = true): Promise<CleanResponse> => {
  const response = await axios.post(`${API_URL}/clean`, { session_id: sessionId, auto_clean: autoClean });
  return response.data;
};

export const runML = async (sessionId: string, targetColumn: string, testSize: number = 0.2): Promise<MLResponse> => {
  const response = await axios.post(`${API_URL}/ml`, { 
    session_id: sessionId, 
    target_column: targetColumn,
    test_size: testSize
  });
  return response.data;
};

export const runInsights = async (sessionId: string): Promise<InsightsResponse> => {
  const response = await axios.post(`${API_URL}/insights`, { session_id: sessionId });
  return response.data;
};

export const runQuery = async (sessionId: string, question: string, crossDataset: boolean = false): Promise<QueryResponse> => {
  const response = await axios.post(`${API_URL}/query`, { 
    session_id: sessionId, 
    question: question,
    cross_dataset: crossDataset
  });
  return response.data;
};

export const generateReport = async (sessionId: string): Promise<Blob> => {
  const response = await axios.post(`${API_URL}/report`, { session_id: sessionId }, {
    responseType: 'blob'
  });
  return response.data;
};

export const getObservatoryStats = async (): Promise<StatsResponse> => {
  const response = await axios.get(`${API_URL}/observatory/stats`);
  return response.data;
};

export const getObservatoryLogs = async (limit: number = 50): Promise<LogEntry[]> => {
  const response = await axios.get(`${API_URL}/observatory/logs?limit=${limit}`);
  return response.data;
};
