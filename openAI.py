import openai
import json
import tiktoken
import concurrent.futures

summaryPromptTemplate = """
Your task is to condense a transcribed meeting into a succinct summary. Please follow these guidelines:

- Provide a comprehensive overview of the meeting, emphasizing the main objectives, outcomes, and themes, ensuring coverage of the entire discussion.
- Enumerate all topics discussed in a list format, including but not limited to the key topics. 
- Identify the action items, specifying the task, the responsible party, and the deadline.
- List any subjects that require further discussion in future meetings.

The summary should encapsulate all pertinent information in a clear, professional manner, avoiding direct quotations. Format your response in JSON as follows:

{
    "summary": "[Your narrative summary here]",
    "topics": ["[Topic 1]", "[Topic 2]", ...],  // List all topics discussed
    "actionItems": ["[Item 1]", "[Item 2]", ...],  // List all action items
    "furtherDiscussionItems": ["[Item 1]", "[Item 2]", ...]  // List topics for further discussion
}
"""


class OpenAIResponse:
    def __init__(self):
        self.summary = ""
        self.actionItems = ""
        self.furtherDiscussionItems = ""
        self.topics = ""
        self.topicsDetails = []
        
    def summaryResponse(self, prompt, text):
        try:
            print("Running Prompt")
            response = openai.ChatCompletion.create(
                model="gpt-4-1106-preview",
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"} 
            )
            rawOutput = response['choices'][0]["message"]["content"]
            return rawOutput
        except Exception as e:
            print(f"Error while making OpenAI API request: {e}")
            return None

    def discussionResponse(self, text):
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        encodedTranscript = encoding.encode(text)
        numberOfTokens = len(encodedTranscript)

        middle = numberOfTokens // 2
        splitIndex = next(i for i, _ in enumerate(encodedTranscript) if i >= middle)

        firstHalf = encodedTranscript[:splitIndex + 1]
        secondHalf = encodedTranscript[splitIndex + 1:]

        firstHalfText = encoding.decode(firstHalf)
        secondHalfText = encoding.decode(secondHalf)

        prompts = [
            """Given this transcript from a recorded meeting. Provide a detailed list of discussion points in this
                meeting transcript. I want a reader to be able to read the list and grasp a clear understanding of 
                everything that was discussed. Structure your response into topics, followed by dot point discussions points""",
            """Given this transcript from a recorded meeting. Provide a detailed list of discussion points in this
                meeting transcript. I want a reader to be able to read the list and grasp a clear understanding of 
                everything that was discussed. Structure your response into topics, followed by dot point discussions points""",
            """Without removing any dicussion points merge these two summaries together such that redudant or duplicate discussion 
               points are removed and the meeting summary is condesended into one summary.
               Return your response as a json format as follows, such that python json library can read it:
               {
                   "topics": [
                       {
                           "topic": "The central theme or subject of discussion",
                           "discussion": ["A detailed list of key points, presented as a narrative summary."]
                       },
                       // Repeat the structure for additional topics
                    ]
                }
            """
        ]

        def fetchResponse(prompt, text, JSON):
            try:
                params = {
                    "model": "gpt-4-1106-preview",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0
                }

                if JSON:
                    params["response_format"] = {"type": "json_object"}

                response = openai.ChatCompletion.create(**params)
                return response['choices'][0]["message"]["content"]
            except Exception as e:
                print(f"Error while making OpenAI API request: {e}")
                return None

        with concurrent.futures.ThreadPoolExecutor() as executor:
            print("Running First and Second Half Prompts")
            futureFirstHalf = executor.submit(fetchResponse, prompts[0], firstHalfText, JSON=False)
            futureSecondHalf = executor.submit(fetchResponse, prompts[1], secondHalfText, JSON=False)
            responses = [futureFirstHalf.result(), futureSecondHalf.result()]
            print(responses)

        
        print("Combining First and Seocnd Half Responses")
        combinedText = "Summary One:" + responses[0] + "Summary Two:" + responses[1]
        combinedResponse = fetchResponse(prompts[2], combinedText, JSON=True)

        print(combinedResponse)
        return combinedResponse
    

    def runPrompts(self, text):
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futureOne = executor.submit(self.summaryResponse, summaryPromptTemplate, text)
                futureTwo = executor.submit(self.discussionResponse, text)

                responseOne = futureOne.result()
                responseTwo = futureTwo.result()

            # Check and process the responses
            if responseOne is None:
                raise ValueError("First response is empty.")
            print(responseOne)
            dataOne = json.loads(responseOne)

            if responseTwo is None:
                raise ValueError("Second response is empty.")
            print(responseTwo)
            dataTwo = json.loads(responseTwo)

            # Process and combine the responses
            self.summary = dataOne.get("summary", "")
            self.topics = dataOne.get("topics", "")
            self.actionItems = dataOne.get("actionItems", [])
            self.furtherDiscussionItems = dataOne.get("furtherDiscussionItems", [])
            self.topicsDetails = dataTwo.get("topics", [])

            topicsDiscussion = ""
            for topicDetail in self.topicsDetails:
                topicTitle = topicDetail.get("topic", "")
                discussionItems = topicDetail.get("discussion", [])
                discussion = "\n".join(f"- {item}" for item in discussionItems)
                topicsDiscussion += f"Topic: {topicTitle}\nDiscussion:\n{discussion}\n\n"

            combinedResponse = {
                "overallSummary": self.summary,
                "topics": self.topics,
                "dicussion": self.topicsDetails,
                "actionItems": self.actionItems,
                "furtherDiscussion": self.furtherDiscussionItems
            }
            print(f"\n\n\n{combinedResponse}\n\n\n")
            return combinedResponse
        
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except ValueError as ve:
            print(f"Value error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        return None

