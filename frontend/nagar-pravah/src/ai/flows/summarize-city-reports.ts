'use server';
/**
 * @fileOverview Summarizes user reports related to a specific location.
 *
 * - summarizeCityReports - A function that summarizes city reports for a given location.
 * - SummarizeCityReportsInput - The input type for the summarizeCityReports function.
 * - SummarizeCityReportsOutput - The return type for the summarizeCityReports function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const SummarizeCityReportsInputSchema = z.object({
  location: z.string().describe('The location to summarize reports for.'),
  reports: z.array(z.string()).describe('Array of user reports related to the location.'),
});
export type SummarizeCityReportsInput = z.infer<typeof SummarizeCityReportsInputSchema>;

const SummarizeCityReportsOutputSchema = z.object({
  summary: z.string().describe('A summary of the user reports for the location.'),
});
export type SummarizeCityReportsOutput = z.infer<typeof SummarizeCityReportsOutputSchema>;

export async function summarizeCityReports(input: SummarizeCityReportsInput): Promise<SummarizeCityReportsOutput> {
  return summarizeCityReportsFlow(input);
}

const prompt = ai.definePrompt({
  name: 'summarizeCityReportsPrompt',
  input: {schema: SummarizeCityReportsInputSchema},
  output: {schema: SummarizeCityReportsOutputSchema},
  prompt: `Summarize the following user reports for the location {{{location}}}.\n\nReports:\n{{#each reports}}- {{{this}}}\n{{/each}}\n\nSummary:`,
});

const summarizeCityReportsFlow = ai.defineFlow(
  {
    name: 'summarizeCityReportsFlow',
    inputSchema: SummarizeCityReportsInputSchema,
    outputSchema: SummarizeCityReportsOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
