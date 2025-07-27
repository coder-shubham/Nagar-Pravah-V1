import AppLayout from "@/components/app-layout";
import ReportForm from "@/components/report/report-form";

export default function ReportPage() {
  return (
    <AppLayout>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-3xl font-bold font-headline tracking-tight">
            Submit a Report
          </h1>
          <p className="text-muted-foreground">
            Share your observations to help improve city insights.
          </p>
        </div>
        <div className="max-w-2xl">
          <ReportForm />
        </div>
      </div>
    </AppLayout>
  );
}
