"use client";

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Story } from "@/lib/types";
import { cn } from "@/lib/utils";
import { TrendingUp, BarChart2, ChevronDown, ChevronUp } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Smile, Frown, Meh } from 'lucide-react';

interface StoryCardProps {
  story: Story;
}

const categoryColors: Record<Story['category'], string> = {
    Traffic: "bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-500/30",
    CivicIssue: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
    Event: "bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500/30",
    Weather: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
    Other: "bg-gray-500/20 text-gray-700 dark:text-gray-400 border-gray-500/30",
};

const severityColors: Record<Story['severity'], string> = {
    High: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
    Medium: "bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-500/30",
    Low: "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-500/30",
    Neutral: "bg-gray-500/20 text-gray-700 dark:text-gray-400 border-gray-500/30",
};

const sentimentEmojis: Record<Story['sentiment'], JSX.Element> = {
    Positive: <Smile className="w-4 h-4 text-green-500" />,
    Negative: <Frown className="w-4 h-4 text-red-500" />,
    Neutral: <Meh className="w-4 h-4 text-gray-500" />,
};

export default function StoryCard({ story }: StoryCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const contentCharacterLimit = 150; // Adjust as needed for 1-2 lines

    const toggleExpand = () => {
        setIsExpanded(!isExpanded);
    };

    const renderContent = () => {
        if (story.content.length <= contentCharacterLimit || isExpanded) {
            return story.content;
        } else {
            return `${story.content.substring(0, contentCharacterLimit)}...`;
        }
    };

  return (
    <Card className="bg-card/60 dark:bg-card/70 backdrop-blur-lg border shadow-lg hover:shadow-xl transition-shadow duration-300 cursor-pointer" onClick={toggleExpand}>
      <CardHeader>
        <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Badge className={cn("font-semibold", categoryColors[story.category])} variant="outline">{story.category}</Badge>
                <Badge className={cn("font-semibold", severityColors[story.severity])} variant="outline">{story.severity}</Badge>
                 {story.sentiment && sentimentEmojis[story.sentiment]}
              </div>
              <CardTitle className="mt-2 font-headline text-xl">{story.title}</CardTitle>
              {story.locationString && (
                  <p className="text-sm text-muted-foreground">{story.locationString}</p>
              )}
            </div>
            {story.isPersonalized && <Badge className="bg-primary/20 text-primary dark:text-primary-foreground border-primary/30">For You</Badge>}
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription>{renderContent()}</CardDescription>
        {story.suggestion && isExpanded && (
            <div className="mt-4 p-3 bg-secondary/50 dark:bg-secondary/70 rounded-md text-secondary-foreground text-sm">
                <strong>Suggestion:</strong> {story.suggestion}
            </div>
        )}
      </CardContent>
      <CardFooter className="flex justify-between text-sm text-muted-foreground">
        <div className="flex gap-4">
            <div className="flex items-center gap-1" title="Priority Score">
                <TrendingUp className="w-4 h-4 text-accent" />
                <span>{story.priorityScore}</span>
            </div>
            <div className="flex items-center gap-1" title="Engagement Count">
                <BarChart2 className="w-4 h-4 text-accent" />
                <span>{story.engagementCount}</span>
            </div>
        </div>
        <div className="flex items-center gap-1">
            <span>{formatDistanceToNow(story.updatedAt, { addSuffix: true })}</span>
            {(story.content.length > contentCharacterLimit || (story.suggestion && !isExpanded)) && (
                 isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
            )}
        </div>
      </CardFooter>
    </Card>
  );
}