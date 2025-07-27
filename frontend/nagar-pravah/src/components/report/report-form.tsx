"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
  } from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast";
import { APIProvider, Map, AdvancedMarker } from "@vis.gl/react-google-maps";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { summarizeCityReports, categorizeEvent } from '@/ai/flows'
import { Card } from "../ui/card";


const formSchema = z.object({
  description: z.string().min(10, {
    message: "Description must be at least 10 characters.",
  }),
  category: z.enum(['traffic', 'safety', 'mood', 'other']),
  location: z.object({
      lat: z.number(),
      lng: z.number()
  })
});

export default function ReportForm() {
    const { toast } = useToast();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    const defaultPosition = { lat: 34.0522, lng: -118.2437 };

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            description: "",
            location: defaultPosition,
        },
    });

    async function onSubmit(values: z.infer<typeof formSchema>) {
        setIsSubmitting(true);
        try {
            // Simulate API calls
            const [categorization] = await Promise.all([
                categorizeEvent({ description: values.description }),
            ]);

            // In a real app, you would POST this data to your backend
            console.log({ ...values, ai_category: categorization.category });

            toast({
                title: "Report Submitted!",
                description: `Your report has been submitted under the category: ${categorization.category}.`,
            });
            form.reset();
        } catch(error) {
            console.error("Submission error", error)
            toast({
                title: "Submission Failed",
                description: "There was an error submitting your report.",
                variant: "destructive"
            });
        } finally {
            setIsSubmitting(false);
        }
    }

    if (!apiKey) {
      return (
        <Card className="h-full flex items-center justify-center">
          <p className="text-muted-foreground">Map functionality is disabled. API key missing.</p>
        </Card>
      );
    }
    
    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                <FormItem>
                    <FormLabel>Observation Description</FormLabel>
                    <FormControl>
                    <Textarea
                        placeholder="Describe what you're seeing in the city..."
                        className="min-h-[120px]"
                        {...field}
                    />
                    </FormControl>
                    <FormMessage />
                </FormItem>
                )}
            />
            <FormField
                control={form.control}
                name="category"
                render={({ field }) => (
                <FormItem>
                    <FormLabel>Category</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                        <SelectTrigger>
                        <SelectValue placeholder="Select a category" />
                        </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                        <SelectItem value="traffic">Traffic</SelectItem>
                        <SelectItem value="safety">Safety</SelectItem>
                        <SelectItem value="mood">Mood</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                    </Select>
                    <FormMessage />
                </FormItem>
                )}
            />
            <FormField
                control={form.control}
                name="location"
                render={({ field }) => (
                <FormItem>
                    <FormLabel>Select Location</FormLabel>
                    <FormDescription>Click on the map to set the report location.</FormDescription>
                    <FormControl>
                    <div className="h-80 w-full rounded-md overflow-hidden border">
                        <APIProvider apiKey={apiKey}>
                            <Map
                                mapId="report-map"
                                style={{ width: '100%', height: '100%' }}
                                defaultCenter={field.value}
                                defaultZoom={13}
                                gestureHandling="greedy"
                                onClick={(e) => {
                                    if(e.detail.latLng) {
                                        field.onChange({lat: e.detail.latLng.lat, lng: e.detail.latLng.lng})
                                    }
                                }}
                            >
                                <AdvancedMarker position={field.value} />
                            </Map>
                        </APIProvider>
                    </div>
                    </FormControl>
                    <FormMessage />
                </FormItem>
                )}
            />
            <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Submit Report
            </Button>
            </form>
        </Form>
    );
}
