import AppLayout from "@/components/app-layout";
import CityPulseMap from "@/components/dashboard/city-pulse-map";

export default function MapPage() {
  return (
    <AppLayout>
      <div className="flex flex-col h-full gap-8">
        <div>
          <h1 className="text-3xl font-bold font-headline tracking-tight">
            City Pulse Map
          </h1>
          <p className="text-muted-foreground">
            Interactive map displaying real-time data points.
          </p>
        </div>
        <div className="flex-grow min-h-[60vh]">
          <CityPulseMap />
        </div>
      </div>
    </AppLayout>
  );
}
