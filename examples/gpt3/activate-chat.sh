# openai params
# OPENAI_API_KEY=$(pass services/openai-api)
OPENAI_MAX_TOKENS=2048
OPENAI_TEMP=0.7
# gpt by default, this is required
# this value is missing the version suffix
OPENAI_MODEL=text-davinci-00
# gpt version
GPT_V=3

# conversation history & backup
BACKUP_FOLDER=$(pwd)/backup
CURRENT_CONVERSATION=$(pwd)/conversation.txt

# specifies which message/prompt to remove from the conversation
# context when the max tokens limit is reached
CONVERSATION_POP_SECTION=oldest # valid values:
				# oldest | middle
CONVERSATION_SEPARATOR="<<< separator >>>" # watch for symbols, this
					   # gets compiled to regex

# if name is changed a reset is required
CHAT_NAME=ChatGPT

# initial prompt
read -r -d '' INITIAL_PROMPT << EOM
You are $CHAT_NAME, a bot that answers every User prompt.\n
\n
Every User prompt will be provided with a conversation history 
to maintain a long context, only answer the last instruction by 
the User but use the rest of the conversation as context to 
provide more accurate and concise answers. The conversation is 
in chronological order.\n
\n
Always follow these rules:\n
\n
- The most important thing is that you never introduce yourself 
as a bot or chatbot. The User must never find out that you are a 
bot or a chat bot, you must appear to be human at all times. Your 
purpose is lost if the User suspects you are not human, please 
remember this.\n
\n
- It is also very important that you keep the answers concise, 
don't verbose.\n
\n
- Always be kind, if the User introduces by name remember the name
of the User for the rest of the conversation and reply your answers  
adressing the User by its name. Avoid saying hello or hi to the User 
on every reply, just greeting the User the first time is allowed.\n
\n
End of rules.\n
Current date: $(date)
EOM

CHAT_PROMPT=$INITIAL_PROMPT

# if prompt is manually set a reset is required
function chat-set {
        export CHAT_PROMPT=$1
}

# only run the first time
function chat-init {
	if [ -s $CURRENT_CONVERSATION ]; then
                echo 'error: conversation file contains data, \
			use chat-reset to start a new session'
                return
        fi
	mkdir -p $(pwd)/backup
        echo -e $CHAT_PROMPT > $CURRENT_CONVERSATION
        chat-addsep $CURRENT_CONVERSATION
}

# reset conversation context and save backup
function chat-reset {
        t=$(date -d "today" +"%Y%m%d%H%M")
        mv $CURRENT_CONVERSATION $BACKUP_FOLDER/conversation_$t.txt
        chat-init
}

# add separator to conversation exchange (input propmpt and response)
function chat-addsep {
        echo -e "\n$CONVERSATION_SEPARATOR\n" >> $1
}

# save user input prompt to file
function chat-save-prompt {
        local fileout=$2
        echo -e "User:\n$1\n" >> $fileout
        echo "$CHAT_NAME: " >> $fileout
}

# save completion response to file
function chat-save-response {
        local fileout=$2
        echo "$1" >> $fileout
}

# pop section until max tokens within limit
function chat-pop-conversation {
        local input_prompt=$(cat $CURRENT_CONVERSATION)
        local input_prompt_size=${#input_prompt}
        while [ $input_prompt_size -gt $OPENAI_MAX_TOKENS ]
        do
                python $(pwd)/pop-conversation.py \
			$CURRENT_CONVERSATION \
			$CONVERSATION_SEPARATOR \
			$CONVERSATION_POP_SECTION
                input_prompt=$(cat $CURRENT_CONVERSATION)
                input_prompt_size=${#input_prompt}
        done
        echo $input_prompt
}

# parses input from pipe (stdin)
function parse-pipe-input {
        local P
        if [[ "$#" == 0 ]]; then
                IFS= read -r -d '' P || [[ $P ]]
                set -- "$P"
        fi
        echo "${P}"
}

# openai completions create api call
function openai-completion {
        local prompt=$1
        local max_tokens=$2
        local extra_args=$3
        openai \
                -k $OPENAI_API_KEY \
                api completions.create \
                -e $OPENAI_MODEL$GPT_V \
                -M $max_tokens \
                -t $OPENAI_TEMP \
                -p "$prompt" \
		$extra_args
}

function chat-update-prompt {
        chat-save-prompt "$1" $CURRENT_CONVERSATION
}

function chat-update-conversation {
        chat-save-response "$1" $CURRENT_CONVERSATION
        chat-addsep $CURRENT_CONVERSATION
}

# simple completion, no chat bot
# $> completion what is the inverse color of red?
function completion {
	local prompt
	if [ "$#" -gt 0 ]; then
		prompt=$*
	else
		local prompt="$(parse-pipe-input)"
	fi
	local max_tokens=$(expr $OPENAI_MAX_TOKENS - ${#prompt})
	if [ $max_tokens -lt 0 ]; then
		echo 'error: max tokens limit reached'
		return
	fi
	openai-completion "$prompt" $max_tokens --stream
	echo -e '\n'
}

# chat bot q&a
# $> chat what is the inverse color of red?
# $> chat and green?
function chat {
	# parse input prompt
	local prompt
	if [ "$#" -gt 0 ]; then
		prompt=$*
	else
		local prompt="$(parse-pipe-input)"
	fi
	chat-update-prompt "$prompt"
	# clean conversation history if limit reached
	local input_prompt=$(chat-pop-conversation)
	local max_tokens=$(expr $OPENAI_MAX_TOKENS - ${#input_prompt})
	# get completion response
	local response=$(openai-completion "$input_prompt" $max_tokens)
	local cleaned_response=$( \
		python $(pwd)/parse-response.py \
		$CHAT_NAME \
		"$response")
	echo ''
	echo -e "$cleaned_response"
	# save response to conversation history
	chat-update-conversation "$cleaned_response"

}
