export interface Stock {
  code: string;
  name: string;
  price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  change: number;
  changePercent: number;
  volume: number;
  amount: number;
}

export interface StockListResponse {
  data: Stock[];
  error?: string;
  message?: string;
}

export type SortOrder = 'asc' | 'desc';

export interface StockListProps {
  codes: string[];
}
