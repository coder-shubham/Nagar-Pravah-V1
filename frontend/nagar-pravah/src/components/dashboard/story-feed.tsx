"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import StoryCard from "./story-card";
import { mockStories } from "@/lib/mock-data";
import type { Story } from "@/lib/types";
import { collection, onSnapshot, query, where } from "firebase/firestore";
import { db, auth } from "../../lib/firebase";
import { onAuthStateChanged } from "firebase/auth";

export default function StoryFeed() {
  const [stories, setStories] = useState<Story[]>([]);
  const [userInterests, setUserInterests] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribeStories = onSnapshot(collection(db, "synthesize-event"), (snapshot) => {
      const fetchedStories: Story[] = [];
      snapshot.forEach((doc) => {
        const data = doc.data();
        fetchedStories.push({
          id: doc.id,
          category: data.category,
          title: data.title,
          content: data.text,
          severity: data.severity,
          suggestion: data.suggestion,
          priorityScore: data.priorityScore,
          engagementCount: data.engagementCount,
          updatedAt: new Date(data.updatedAt.toDate()),
          locationString: data.locationString,
          sentiment: data.sentiment,
        } as Story);
      });
      setStories(fetchedStories.length > 0 ? fetchedStories : mockStories);
      setLoading(false);
    }, (error) => {
      console.error("Error fetching stories:", error);
      setStories(mockStories);
      setLoading(false);
    });

    const unsubscribeAuth = onAuthStateChanged(auth, (user) => {
      if (user) {
        const unsubscribeInterests = onSnapshot(query(collection(db, "user-profile"), where("userId", "==", user.uid)), (snapshot) => {
          snapshot.forEach((doc) => {
            const userData = doc.data();
            setUserInterests(userData.interests || []);
          });
        }, (error) => {
          console.error("Error fetching user interests:", error);
          setUserInterests([]);
        });
        return () => unsubscribeInterests();
      } else {
        setUserInterests([]);
      }
    });

    return () => {
      unsubscribeStories();
      unsubscribeAuth();
    };
  }, []);

  const trendingStories = [...stories]
    .sort((a, b) => b.priorityScore - a.priorityScore || b.engagementCount - a.engagementCount)
    .slice(0, 5);

  const personalizedStories = stories.filter(story => 
    userInterests.some(interest => interest === story.category)
  );

  if (loading) {
    return <div className="text-center text-muted-foreground py-8">Loading stories...</div>;
  }

  return (
    <Tabs defaultValue="trending" className="w-full">
      <TabsList className="grid w-full grid-cols-3 md:w-auto md:grid-cols-3 bg-muted/60">
        <TabsTrigger value="trending">Trending</TabsTrigger>
        <TabsTrigger value="overall">Overall</TabsTrigger>
        <TabsTrigger value="personalized">Personalized</TabsTrigger>
      </TabsList>
      <TabsContent value="trending">
        <div className="grid gap-4 mt-4">
          {trendingStories.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
        </div>
      </TabsContent>
      <TabsContent value="overall">
        <div className="grid gap-4 mt-4">
          {stories.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
        </div>
      </TabsContent>
      <TabsContent value="personalized">
        <div className="grid gap-4 mt-4">
          {personalizedStories.length > 0 ? (
            personalizedStories.map((story) => (
              <StoryCard key={story.id} story={story} />
            ))
          ) : (
            <div className="text-center text-muted-foreground py-8">
              No personalized stories yet.
            </div>
          )}
        </div>
      </TabsContent>
    </Tabs>
  );
}
