import AppLayout from "@/components/app-layout";
import ProfileForm from "@/components/profile/profile-form";

export default function ProfilePage() {
  return (
    <AppLayout>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-3xl font-bold font-headline tracking-tight">
            Profile & Preferences
          </h1>
          <p className="text-muted-foreground">
            Manage your personal information and personalization settings.
          </p>
        </div>
        <div className="max-w-4xl">
          <ProfileForm />
        </div>
      </div>
    </AppLayout>
  );
}
