import AppLayout from "@/components/app-layout";
import StoryFeed from "@/components/dashboard/story-feed";

export default function Home() {
  return (
    <AppLayout>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-3xl font-bold font-headline tracking-tight">
            Story Feed
          </h1>
          <p className="text-muted-foreground">
            Real-time display of synthesized events and stories.
          </p>
        </div>
        <StoryFeed />
      </div>
    </AppLayout>
  );
}
