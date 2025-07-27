import { GeoPoint } from "firebase/firestore";
import { Story, MapPoint } from "./types";

const bangaloreCoordinates = {
  lat: 12.9716,
  lng: 77.5946,
};

// Function to generate a random coordinate within a radius around a center point
function getRandomCoordinate(center: { lat: number; lng: number }, radiusInMeters: number) {
  const y0 = center.lat;
  const x0 = center.lng;
  const rd = radiusInMeters / 111300; //about 111300 meters in one degree

  const u = Math.random();
  const v = Math.random();
  const w = rd * Math.sqrt(u);
  const t = 2 * Math.PI * v;
  const x = w * Math.cos(t);
  const y = w * Math.sin(t);

  const newLat = y + y0;
  const newLng = x + x0;

  return { lat: newLat, lng: newLng };
}

// Generate random coordinates around Bangalore
const randomCoord1 = getRandomCoordinate(bangaloreCoordinates, 10000); // within 10 km
const randomCoord2 = getRandomCoordinate(bangaloreCoordinates, 15000); // within 15 km
const randomCoord3 = getRandomCoordinate(bangaloreCoordinates, 8000); // within 8 km
const randomCoord4 = getRandomCoordinate(bangaloreCoordinates, 12000); // within 12 km
const randomCoord5 = getRandomCoordinate(bangaloreCoordinates, 5000); // within 5 km
const randomCoord6 = getRandomCoordinate(bangaloreCoordinates, 7000); // within 7 km

export const mockStories: Story[] = [
  {
    id: "1",
    category: "Traffic",
    title: "Heavy Congestion on Inner Ring Road",
    content: "Reports of significant traffic delays on Inner Ring Road due to an overturned vehicle near the Ejipura flyover. Authorities are on the scene diverting traffic.",
    severity: "High",
    priorityScore: 95,
    engagementCount: 150, // Changed from mentionCount
    updatedAt: new Date(Date.now() - 10 * 60 * 1000), // Changed from timestamp
    isPersonalized: false,
    locationString: "Inner Ring Road, Bangalore", // Added locationString
    sentiment: "Negative", // Added sentiment
  },
  {
    id: "2",
    category: "Event",
    title: "Tech Conference at KTPO",
    content: "A major tech conference is underway at KTPO, Whitefield, attracting a large crowd. Expect increased traffic in the surrounding areas.",
    severity: "Medium",
    priorityScore: 80,
    engagementCount: 80, // Changed from mentionCount
    updatedAt: new Date(Date.now() - 60 * 60 * 1000), // Changed from timestamp
    isPersonalized: true,
    locationString: "KTPO, Whitefield", // Added locationString
    sentiment: "Neutral", // Added sentiment
  },
  {
    id: "3",
    category: "CivicIssue", // Changed from Safety
    title: "Potholes Reported in BTM Layout",
    content: "Several complaints received about large potholes on key roads in BTM Layout, causing inconvenience to commuters and posing a safety risk.",
    severity: "High",
    priorityScore: 90,
    engagementCount: 120, // Changed from mentionCount
    updatedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // Changed from timestamp
    isPersonalized: false,
    suggestion: "Commuters are advised to take alternative routes or exercise caution while driving in BTM Layout.",
    locationString: "BTM Layout, Bangalore", // Added locationString
    sentiment: "Negative", // Added sentiment
  },
    {
    id: "4",
    category: "Weather", // Changed from Mood
    title: "Heavy Rainfall Expected",
    content: "The meteorological department has issued a warning for heavy rainfall in the city over the next 24 hours. Expect potential waterlogging in low-lying areas.",
    severity: "Medium",
    priorityScore: 75,
    engagementCount: 50, // Changed from mentionCount
    updatedAt: new Date(Date.now() - 12 * 60 * 60 * 1000), // Changed from timestamp
    isPersonalized: false,
    locationString: "Bangalore", // Added locationString
    sentiment: "Neutral", // Added sentiment
  },
      {
    id: "5",
    category: "Other",
    title: "Power Outage in Jayanagar",
    content: "An unexpected power outage has been reported in parts of Jayanagar. Electricity board is working to restore the power supply.",
    severity: "Low",
    priorityScore: 60,
    engagementCount: 30, // Changed from mentionCount
    updatedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000), // Changed from timestamp
    isPersonalized: true,
    locationString: "Jayanagar, Bangalore", // Added locationString
    sentiment: "Negative", // Added sentiment
  },
];

export const mockMapPoints: MapPoint[] = [
  {
    id: "1",
    locationGeo: new GeoPoint(randomCoord1.lat, randomCoord1.lng),
    category: "Traffic",
    content: "Heavy traffic reported at Silk Board junction, Bangalore.",
    title: "Traffic Alert",
    sentiment: "Negative",
    status: "Active",
    suggestion: "Avoid the area or take alternative routes.",
  },
  {
    id: "2",
    locationGeo: new GeoPoint(randomCoord2.lat, randomCoord2.lng),
    category: "Event",
    content: "Annual music festival happening at Palace Grounds, Bangalore.",
    title: "Music Festival",
    sentiment: "Positive",
    status: "Active",
    suggestion: "Expect crowds and plan your commute accordingly.",
  },
  {
    id: "3",
    locationGeo: new GeoPoint(randomCoord3.lat, randomCoord3.lng),
    category: "CivicIssue",
    content: "Potholes reported on the main road near Indiranagar, Bangalore.",
    title: "Road Condition",
    sentiment: "Negative",
    status: "Active",
    suggestion: "Drive carefully and report any further issues.",
  },
  {
    id: "4",
    locationGeo: new GeoPoint(randomCoord4.lat, randomCoord4.lng),
    category: "Weather",
    content: "Heavy rainfall expected in Bangalore today.",
    title: "Weather Forecast",
    sentiment: "Neutral",
    status: "Future",
    suggestion: "Carry an umbrella and be prepared for potential waterlogging.",
  },
  {
    id: "5",
    locationGeo: new GeoPoint(randomCoord5.lat, randomCoord5.lng),
    category: "Other",
    content: "Local marathon event in Bangalore is causing road closures.",
    title: "Marathon Event",
    sentiment: "Positive",
    status: "Active",
    suggestion: "Check for alternative routes and expect delays.",
  },
  {
    id: "6",
    locationGeo: new GeoPoint(randomCoord6.lat, randomCoord6.lng),
    category: "Traffic",
    content: "Traffic cleared up at Silk Board junction, Bangalore.",
    title: "Traffic Update",
    sentiment: "Positive",
    status: "Past",
  },
];