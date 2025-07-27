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
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/context/auth-context";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Switch } from "../ui/switch";
import { useState, useEffect } from "react";
import { APIProvider, Map, AdvancedMarker } from "@vis.gl/react-google-maps";
import { Loader2 } from "lucide-react";
import { db } from "@/lib/firebase";
import { doc, setDoc, GeoPoint } from "firebase/firestore";

const formSchema = z.object({
  displayName: z.string().min(2, "Name must be at least 2 characters."),
  interests: z.object({
    traffic: z.boolean().default(false),
    event: z.boolean().default(false),
    civicIssue: z.boolean().default(false),
    weather: z.boolean().default(false),
  }),
  homeLocation: z.object({ lat: z.number(), lng: z.number() }),
  workLocation: z.object({ lat: z.number(), lng: z.number() }),
});

export default function ProfileForm() {
    const { toast } = useToast();
    const { user, logout } = useAuth();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

    const defaultLocation = { lat: 12.9716, lng: 77.5946 }; // Center of Bangalore

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            displayName: user?.displayName || "",
            interests: { 
                traffic: user?.interests.includes('Traffic') || false,
                event: user?.interests.includes('Event') || false,
                civicIssue: user?.interests.includes('CivicIssue') || false,
                weather: user?.interests.includes('Weather') || false,
            }, 
            homeLocation: user?.homeLocation ? { lat: user.homeLocation.latitude, lng: user.homeLocation.longitude } : defaultLocation,
            workLocation: user?.workLocation ? { lat: user.workLocation.latitude, lng: user.workLocation.longitude } : defaultLocation,
        },
    });

    // Update form defaults when user data loads
    useEffect(() => {
        if (user) {
            form.reset({
                displayName: user.displayName || "",
                interests: {
                    traffic: user.interests.includes('Traffic') || false,
                    event: user.interests.includes('Event') || false,
                    civicIssue: user.interests.includes('CivicIssue') || false,
                    weather: user.interests.includes('Weather') || false,
                },
                homeLocation: user.homeLocation ? { lat: user.homeLocation.latitude, lng: user.homeLocation.longitude } : defaultLocation,
                workLocation: user.workLocation ? { lat: user.workLocation.latitude, lng: user.workLocation.longitude } : defaultLocation,
            });
        }
    }, [user, form]);

    async function onSubmit(values: z.infer<typeof formSchema>) {
        setIsSubmitting(true);
        console.log("Saving profile data:", values);
        
        if (user) {
            const updatedInterests = Object.entries(values.interests)
                .filter(([key, value]) => value)
                .map(([key]) => {
                    switch (key) {
                        case 'traffic': return 'Traffic';
                        case 'event': return 'Event';
                        case 'civicIssue': return 'CivicIssue';
                        case 'weather': return 'Weather';
                        default: return '';
                    }
                }).filter(interest => interest !== '');

            const updatedHomeLocation = new GeoPoint(values.homeLocation.lat, values.homeLocation.lng);
            const updatedWorkLocation = new GeoPoint(values.workLocation.lat, values.workLocation.lng);

            try {
                await setDoc(doc(db, "user-profile", user.uid), {
                    ...user,
                    displayName: values.displayName,
                    interests: updatedInterests,
                    homeLocation: updatedHomeLocation,
                    workLocation: updatedWorkLocation,
                    updatedAt: new Date(), // Consider using Firestore Timestamp.now() here
                }, { merge: true });
                toast({ title: "Profile Updated", description: "Your preferences have been saved." });
            } catch (error) {
                console.error("Error saving profile data:", error);
                toast({ title: "Error", description: "Failed to save profile.", variant: "destructive" });
            }
        } else {
            toast({ title: "Error", description: "User not authenticated.", variant: "destructive" });
        }

        setIsSubmitting(false);
    }
    
    const LocationPicker = ({ field, label }: { field: any, label: string }) => (
        <FormItem>
            <FormLabel>{label}</FormLabel>
            <FormControl>
                <div className="h-60 w-full rounded-md overflow-hidden border">
                    {apiKey ? (
                        <APIProvider apiKey={apiKey}>
                            <Map
                                mapId={`map-${field.name}`}
                                style={{ width: '100%', height: '100%' }}
                                center={field.value} // Use center instead of defaultCenter
                                defaultZoom={14}
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
                    ) : (
                        <div className="flex items-center justify-center h-full bg-muted">
                            <p className="text-muted-foreground text-sm">Map disabled</p>
                        </div>
                    )}
                </div>
            </FormControl>
            <FormMessage />
        </FormItem>
    );

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <Card>
          <CardHeader>
            <CardTitle className="font-headline">Personal Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="displayName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Display Name</FormLabel>
                  <FormControl><Input placeholder="Your Name" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
            <CardHeader><CardTitle className="font-headline">Interests</CardTitle></CardHeader>
            <CardContent className="space-y-4">
                <FormDescription>Select topics you're interested in for personalized stories.</FormDescription>
                <FormField control={form.control} name="interests.traffic" render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4"><FormLabel>Traffic</FormLabel><FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl></FormItem>
                )} />
                <FormField control={form.control} name="interests.event" render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4"><FormLabel>Events</FormLabel><FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl></FormItem>
                )} />
                <FormField control={form.control} name="interests.civicIssue" render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4"><FormLabel>Civic Issue</FormLabel><FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl></FormItem>
                )} />
                <FormField control={form.control} name="interests.weather" render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4"><FormLabel>Weather</FormLabel><FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl></FormItem>
                )} />
            </CardContent>
        </Card>
        
        <Card>
            <CardHeader><CardTitle className="font-headline">Locations</CardTitle></CardHeader>
            <CardContent className="grid md:grid-cols-2 gap-8">
                <FormField control={form.control} name="homeLocation" render={({ field }) => <LocationPicker field={field} label="Home Location" />} />
                <FormField control={form.control} name="workLocation" render={({ field }) => <LocationPicker field={field} label="Work Location" />} />
            </CardContent>
        </Card>

        <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
        </Button>
        
        <Button variant="outline" onClick={logout} disabled={isSubmitting}>
            Logout
        </Button>
      </form>
    </Form>
  );
}