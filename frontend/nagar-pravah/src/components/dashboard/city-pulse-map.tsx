"use client";

import {
  APIProvider,
  Map,
  AdvancedMarker,
  InfoWindow,
} from "@vis.gl/react-google-maps";
import { useState, useEffect } from "react";
import { Card, CardContent } from "../ui/card";
import { mockMapPoints } from "@/lib/mock-data";
import { MapPoint } from "@/lib/types";
import { Button } from "../ui/button";
import {
  Car,
  AlertTriangle,
  Smile,
  MapIcon,
  Cloud,
  ChevronDownIcon,
} from "lucide-react";
import { Badge } from "../ui/badge";
import { GeoPoint } from "firebase/firestore";
import { collection, onSnapshot, query, where } from "firebase/firestore";
import { db } from "@/lib/firebase";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";

const markerIcons = {
  Traffic: <Car className="h-5 w-5 text-white" />,
  CivicIssue: <AlertTriangle className="h-5 w-5 text-white" />,
  Event: <MapIcon className="h-5 w-5 text-white" />,
  Weather: <Cloud className="h-5 w-5 text-white" />,
  Other: <MapIcon className="h-5 w-5 text-white" />,
  Positive: <Smile className="h-5 w-5 text-white" />,
  Negative: <Smile className="h-5 w-5 text-white" />,
  Neutral: <Smile className="h-5 w-5 text-white" />,
};

const markerColors = {
  Traffic: "bg-orange-500",
  CivicIssue: "bg-red-500",
  Event: "bg-purple-500",
  Weather: "bg-blue-500",
  Other: "bg-gray-500",
  Positive: "bg-green-500",
  Negative: "bg-red-500",
  Neutral: "bg-yellow-500",
};

export default function CityPulseMap() {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  const [selectedPoint, setSelectedPoint] = useState<MapPoint | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<
    | "All"
    | "Mood"
    | "Traffic"
    | "Event"
    | "Weather"
    | "CivicIssue"
    | "Personalize"
  >("All");
  const [statusFilter, setStatusFilter] = useState<
    "All" | "Active" | "Past" | "Future"
  >("All");
  const [mapPoints, setMapPoints] = useState<MapPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userStoryIds, setUserStoryIds] = useState<string[]>([]);

  // Replace with actual user ID logic
  const currentUserId = "user123";

  useEffect(() => {
    let unsubscribeMap: (() => void) | null = null;
    let unsubscribeUserEvents: (() => void) | null = null;

    const fetchMapData = async () => {
      setLoading(true);
      setError(null);
      try {
        const q = query(collection(db, "synthesize-event"));
        unsubscribeMap = onSnapshot(
          q,
          (snapshot) => {
            const points: MapPoint[] = [];
            snapshot.forEach((doc) => {
              const data = doc.data();
              if (data.locationGeo instanceof GeoPoint) {
                points.push({
                  id: doc.id,
                  locationGeo: data.locationGeo,
                  category: data.category,
                  content: data.content,
                  title: data.title,
                  updatedAt: data.updatedAt,
                  sentiment: data.sentiment,
                  status: data.status,
                  suggestion: data.suggestion,
                });
              }
            });
            setMapPoints(points);
            setLoading(false);
          },
          (err) => {
            console.error("Error fetching map data:", err);
            setError(err.message);
            setMapPoints([]);
            setLoading(false);
          }
        );
      } catch (err: any) {
        console.error("Error fetching map data:", err);
        setError(err.message);
        setMapPoints([]);
        setLoading(false);
      }
    };

    const fetchUserRouteEvents = async () => {
      if (!currentUserId) return;
      try {
        const q = query(
          collection(db, "user-route-event"),
          where("userId", "==", currentUserId)
        );
        unsubscribeUserEvents = onSnapshot(q, (snapshot) => {
          const storyIds: string[] = [];
          snapshot.forEach((doc) => {
            const data = doc.data();
            if (data.storyIds && Array.isArray(data.storyIds)) {
              storyIds.push(...data.storyIds);
            }
          });
          setUserStoryIds(storyIds);
        });
      } catch (err) {
        console.error("Error fetching user route events:", err);
      }
    };

    fetchMapData();
    fetchUserRouteEvents();

    return () => {
      if (unsubscribeMap) {
        unsubscribeMap();
      }
      if (unsubscribeUserEvents) {
        unsubscribeUserEvents();
      }
    };
  }, [currentUserId]);

  const displayPoints =
    error || (!loading && mapPoints.length === 0)
      ? mockMapPoints
      : mapPoints;

  const filteredPoints = displayPoints.filter((point) => {
    const categoryMatch =
      categoryFilter === "All"
        ? true
        : categoryFilter === "Mood"
        ? point.sentiment !== undefined
        : categoryFilter === "Personalize"
        ? userStoryIds.includes(point.id)
        : point.category === categoryFilter;

    const statusMatch =
      statusFilter === "All" ? true : point.status === statusFilter;

    return categoryMatch && statusMatch;
  });

  const getStatusIcon = (status: "All" | "Active" | "Past" | "Future") => {
    switch (status) {
      case "Active":
        return "🟢"; // Green circle
      case "Past":
        return "⚪"; // White circle
      case "Future":
        return "🔵"; // Blue circle
      default:
        return ""; // No icon for All
    }
  };

  if (!apiKey) {
    return (
      <Card className="h-full flex items-center justify-center">
        <CardContent className="text-center">
          <p className="text-lg font-semibold">Map not available</p>
          <p className="text-muted-foreground">
            Google Maps API key is missing.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <APIProvider apiKey={apiKey}>
      <div className="h-full w-full relative">
        <div className="absolute top-4 left-4 z-10 bg-background/80 p-2 rounded-lg shadow-lg backdrop-blur-sm">
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={categoryFilter === "All" ? "default" : "outline"}
              onClick={() => setCategoryFilter("All")}
            >
              All
            </Button>
            <Button
              size="sm"
              variant={categoryFilter === "Mood" ? "default" : "outline"}
              onClick={() => setCategoryFilter("Mood")}
            >
              Mood
            </Button>
            <Button
              size="sm"
              variant={categoryFilter === "Traffic" ? "default" : "outline"}
              onClick={() => setCategoryFilter("Traffic")}
            >
              Traffic
            </Button>
            <Button
              size="sm"
              variant={categoryFilter === "Event" ? "default" : "outline"}
              onClick={() => setCategoryFilter("Event")}
            >
              Event
            </Button>
            <Button
              size="sm"
              variant={categoryFilter === "Weather" ? "default" : "outline"}
              onClick={() => setCategoryFilter("Weather")}
            >
              Weather
            </Button>
            <Button
              size="sm"
              variant={categoryFilter === "CivicIssue" ? "default" : "outline"}
              onClick={() => setCategoryFilter("CivicIssue")}
            >
              CivicIssue
            </Button>
            <Button
              size="sm"
              variant={categoryFilter === "Personalize" ? "default" : "outline"}
              onClick={() => setCategoryFilter("Personalize")}
            >
              Personalize
            </Button>
          </div>
        </div>

        <div className="absolute top-4 right-4 z-10 bg-background/80 p-2 rounded-lg shadow-lg backdrop-blur-sm">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="flex items-center gap-1">
                {statusFilter === "All" ? (
                  "All Status"
                ) : (
                  <span className="mr-1">{getStatusIcon(statusFilter)}</span>
                )}
                {statusFilter !== "All" && statusFilter}
                <ChevronDownIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setStatusFilter("All")}>
                All Status
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("Active")}>
                {getStatusIcon("Active")} Live
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("Past")}>
                {getStatusIcon("Past")} Past
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter("Future")}>
                {getStatusIcon("Future")} Future
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <Map
          mapId="nagar-pravah-map"
          style={{ width: "100%", height: "100%", borderRadius: "var(--radius)" }}
          defaultCenter={{ lat: 12.9716, lng: 77.5946 }}
          defaultZoom={12}
          gestureHandling={"greedy"}
          disableDefaultUI={true}
        >
          {filteredPoints.map((point) => (
            <AdvancedMarker
              key={point.id}
              position={{
                lat: point.locationGeo.latitude,
                lng: point.locationGeo.longitude,
              }}
              onClick={() => setSelectedPoint(point)}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-white shadow-md ${
                  categoryFilter === "Mood"
                    ? markerColors[point.sentiment]
                    : markerColors[point.category]
                }`}
              >
                {categoryFilter === "Mood"
                  ? markerIcons[point.sentiment]
                  : markerIcons[point.category]}
              </div>
            </AdvancedMarker>
          ))}
          {selectedPoint &&
            (categoryFilter !== "Personalize" ? (
              <InfoWindow
                position={{
                  lat: selectedPoint.locationGeo.latitude,
                  lng: selectedPoint.locationGeo.longitude,
                }}
                onCloseClick={() => setSelectedPoint(null)}
              >
                <div className="p-2">
                  <Badge
                    variant="outline"
                    className={`font-semibold ${
                      categoryFilter === "Mood"
                        ? markerColors[selectedPoint.sentiment]
                        : markerColors[selectedPoint.category]
                    } text-white`}
                  >
                    {categoryFilter === "Mood"
                      ? selectedPoint.sentiment
                      : selectedPoint.category}
                  </Badge>
                  <h3 className="mt-2 text-lg font-semibold text-foreground">
                    {selectedPoint.title}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {selectedPoint.content}
                  </p>
                  {selectedPoint.suggestion && (
                    <p className="text-sm text-blue-600 italic mt-1">
                      Suggestion: {selectedPoint.suggestion}
                    </p>
                  )}
                </div>
              </InfoWindow>
            ) : (
              <InfoWindow
                position={{
                  lat: selectedPoint.locationGeo.latitude,
                  lng: selectedPoint.locationGeo.longitude,
                }}
                onCloseClick={() => setSelectedPoint(null)}
              >
                <div className="p-2">
                  <h3 className="mt-2 text-lg font-semibold text-foreground">
                    {selectedPoint.title}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {selectedPoint.content}
                  </p>
                  {selectedPoint.suggestion && (
                    <p className="text-sm text-blue-600 italic mt-1">
                      Suggestion: {selectedPoint.suggestion}
                    </p>
                  )}
                </div>
              </InfoWindow>
            ))}
        </Map>
      </div>
    </APIProvider>
  );
}