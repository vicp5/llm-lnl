# Small implementation of a Chat bot with GPT

Small example implementation of a chat bot leveraging OpenAI's GPT. Requires an API Key for Open AI API.

`export OPENAI_API_KEY=XXXXXXXXXXX`

## Usage

Activate the chat within this folder:

`source activate-chat.sh`

### Initialize

Initialize chat if it is the first time:

`chat-init`

You can always reset the state of the chat:

`chat-reset`

Or change the initial prompt:

`chat-set "You are a bot that answers questions"`

`chat-reset`

### Simple prompts/questions (no chat bot)

`completion what is the differente between ai and machine learning?`

You can also pipe a large prompt from a file:

`cat long_prompt.txt | completion`

### Chat bot

`chat what is the inverse color of green?`

`chat and red?`

You can also pipe a large prompt from a file, beware of max tokens limit:

`cat long_prompt.txt | chat`

### Conversation

Chat conversation is kept in the conversation.txt file. Every time the chat is reset the current conversation is saved in the backup folder with a timestamp.
