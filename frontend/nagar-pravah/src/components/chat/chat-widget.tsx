"use client";

import { useState, useRef, useEffect } from "react";
import { MessageSquare, Mic, Send, Volume2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "../ui/scroll-area";
import { Avatar, AvatarFallback } from "../ui/avatar";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { generateCityInsights } from "@/ai/flows/generate-city-insights";
import { v4 as uuidv4 } from 'uuid';

interface Message {
  id: number;
  text: string;
  sender: "user" | "ai";
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const { toast } = useToast();
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (isOpen && !sessionId) {
      setSessionId(uuidv4());
    } else if (!isOpen && sessionId) {
      setSessionId(null);
      setMessages([]);
    }
  }, [isOpen, sessionId]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !sessionId || isSending) return;

    const userMessage: Message = { id: Date.now(), text: inputValue, sender: "user" };
    setMessages(prev => [...prev, userMessage]);
    const query = inputValue;
    setInputValue("");
    setIsSending(true);

    try {
      // Replace with your actual API endpoint and userId logic
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query, userId: 'testuser2', sessionId: sessionId }),
      });

      const data = await response.json();
      const aiMessage: Message = { id: Date.now() + 1, text: data.response, sender: "ai" };
      setMessages(prev => [...prev, aiMessage]);
      speak(data.response);
    } catch (error) {
      console.error("Chat API Error:", error);
      const errorMessage: Message = { id: Date.now() + 1, text: "Sorry, I couldn't process that.", sender: "ai" };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
    }
  };
  
  const speak = (text: string) => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
    }
  };

  const handleVoiceInput = () => {
    if (!('webkitSpeechRecognition' in window)) {
        toast({ title: "Voice recognition not supported", description: "Please use a supported browser like Chrome.", variant: "destructive"});
        return;
    }

    if (isListening) {
        recognitionRef.current?.stop();
        setIsListening(false);
        return;
    }

    const recognition = new (window as any).webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = (event: any) => {
        toast({ title: "Voice recognition error", description: event.error, variant: "destructive"});
    };
    recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInputValue(transcript);
    };

    recognition.start();
    recognitionRef.current = recognition;
  };

  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollAreaRef.current) {
        const scrollableView = scrollAreaRef.current.querySelector('div[data-radix-scroll-area-viewport]');
        if (scrollableView) {
            scrollableView.scrollTop = scrollableView.scrollHeight;
        }
    }
  }, [messages]);

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button
          className="fixed bottom-6 right-6 h-16 w-16 rounded-full shadow-2xl z-20"
          size="icon"
        >
          <MessageSquare className="h-8 w-8" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px] flex flex-col p-0">
        <SheetHeader className="p-6 border-b">
          <SheetTitle className="font-headline">Conversational AI</SheetTitle>
        </SheetHeader>
        <ScrollArea className="flex-1" ref={scrollAreaRef}>
          <div className="p-6 space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={cn("flex items-end gap-2", message.sender === "user" ? "justify-end" : "justify-start")}>
                {message.sender === "ai" && (
                    <Avatar className="h-8 w-8">
                        <AvatarFallback>AI</AvatarFallback>
                    </Avatar>
                )}
                 <div className={cn("max-w-[75%] rounded-lg px-4 py-2", message.sender === "user" ? "bg-primary text-primary-foreground" : "bg-muted")}>
                    <p className="text-sm">{message.text}</p>
                 </div>
                 {message.sender === "user" && (
                    <Avatar className="h-8 w-8">
                        <AvatarFallback>U</AvatarFallback>
                    </Avatar>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
        <div className="p-4 border-t bg-background">
          <div className="relative">
            <Input
              placeholder="Ask about the city..."
              className="pr-20"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
              disabled={isSending}
            />
            <div className="absolute inset-y-0 right-0 flex items-center">
                <Button variant="ghost" size="icon" onClick={handleVoiceInput}>
                    <Mic className={cn("h-5 w-5", isListening && "text-destructive animate-pulse")} />
                </Button>
                <Button variant="ghost" size="icon" onClick={handleSendMessage} disabled={isSending}>
                    <Send className="h-5 w-5" />
                </Button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
