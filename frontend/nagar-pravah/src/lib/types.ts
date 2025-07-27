import { GeoPoint } from "firebase/firestore";

export type Story = {
  id: string;
  category: 'Traffic' | 'CivicIssue' | 'Event' | 'Weather' | 'Other';
  title: string;
  content: string;
  severity: 'High' | 'Medium' | 'Low' | 'Neutral';
  suggestion?: string;
  priorityScore: number;
  engagementCount: number;
  updatedAt: Date;
  isPersonalized?: boolean;
  locationString?: string;
  sentiment: 'Positive' | 'Negative' | 'Neutral';
};

export type MapPoint = {
  id: string;
  locationGeo: GeoPoint;
  category: 'Traffic' | 'CivicIssue' | 'Event' | 'Weather' | 'Other';
  content: string;
  title?: string;
  updatedAt?: any;
  sentiment: 'Positive' | 'Negative' | 'Neutral';
  status: 'Active' | 'Past' | 'Future';
  suggestion?: string;
};