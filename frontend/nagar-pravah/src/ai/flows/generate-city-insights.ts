'use server';

/**
 * @fileOverview A city insights generation AI agent.
 *
 * - generateCityInsights - A function that handles the city insights generation process.
 * - GenerateCityInsightsInput - The input type for the generateCityInsights function.
 * - GenerateCityInsightsOutput - The return type for the generateCityInsights function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GenerateCityInsightsInputSchema = z.object({
  cityData: z.string().describe('Real-time city data as a JSON string.'),
});
export type GenerateCityInsightsInput = z.infer<typeof GenerateCityInsightsInputSchema>;

const GenerateCityInsightsOutputSchema = z.object({
  narrative: z.string().describe('A narrative summary of the city data.'),
  priorityScore: z.number().describe('A score indicating the priority or importance of the event'),
  mentionCount: z.number().describe('The number of times event is mentioned'),
});
export type GenerateCityInsightsOutput = z.infer<typeof GenerateCityInsightsOutputSchema>;

export async function generateCityInsights(input: GenerateCityInsightsInput): Promise<GenerateCityInsightsOutput> {
  return generateCityInsightsFlow(input);
}

const prompt = ai.definePrompt({
  name: 'generateCityInsightsPrompt',
  input: {schema: GenerateCityInsightsInputSchema},
  output: {schema: GenerateCityInsightsOutputSchema},
  prompt: `You are an AI agent specializing in generating insights and narratives from city data.

  Given the following real-time city data, synthesize a meaningful narrative that helps users understand what is happening in the city.
  Also generate the priority score and number of times event is mentioned.

  City Data: {{{cityData}}}
  Output narrative, priorityScore and mentionCount in JSON format.
  `,
});

const generateCityInsightsFlow = ai.defineFlow(
  {
    name: 'generateCityInsightsFlow',
    inputSchema: GenerateCityInsightsInputSchema,
    outputSchema: GenerateCityInsightsOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
