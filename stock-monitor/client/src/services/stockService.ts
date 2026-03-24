import axios from 'axios';
import type { StockListResponse } from '../types/stock';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export async function getStockList(codes: string[]): Promise<StockListResponse> {
  const response = await api.get<StockListResponse>('/stocks', {
    params: { codes: codes.join(',') },
  });
  return response.data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await api.get('/health');
    return response.data.status === 'ok';
  } catch {
    return false;
  }
}
