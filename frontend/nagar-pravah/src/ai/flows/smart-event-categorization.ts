'use server';
/**
 * @fileOverview This file implements a Genkit flow for categorizing user reports using AI.
 *
 * - categorizeEvent - A function that categorizes an event based on its description.
 * - CategorizeEventInput - The input type for the categorizeEvent function.
 * - CategorizeEventOutput - The return type for the categorizeEvent function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const CategorizeEventInputSchema = z.object({
  description: z.string().describe('The description of the event to categorize.'),
});
export type CategorizeEventInput = z.infer<typeof CategorizeEventInputSchema>;

const CategorizeEventOutputSchema = z.object({
  category: z
    .enum(['traffic', 'safety', 'mood', 'other'])
    .describe('The category of the event.'),
});
export type CategorizeEventOutput = z.infer<typeof CategorizeEventOutputSchema>;

export async function categorizeEvent(input: CategorizeEventInput): Promise<CategorizeEventOutput> {
  return categorizeEventFlow(input);
}

const prompt = ai.definePrompt({
  name: 'categorizeEventPrompt',
  input: {schema: CategorizeEventInputSchema},
  output: {schema: CategorizeEventOutputSchema},
  prompt: `You are an AI assistant specializing in categorizing user-submitted events.

  Given the following event description, determine the most appropriate category.

  Event Description: {{{description}}}

  The category should be one of the following: traffic, safety, mood, or other.
  Return the category in JSON format.
`,
});

const categorizeEventFlow = ai.defineFlow(
  {
    name: 'categorizeEventFlow',
    inputSchema: CategorizeEventInputSchema,
    outputSchema: CategorizeEventOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
