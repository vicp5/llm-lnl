# OPENAI_API_KEY=$(pass services/openai.com)
OPENAI_COMPLETION_MODEL=text-davinci-003
OPENAI_MAX_TOKENS=2048
OPENAI_TEMP=0.7

# conversation history & backup
BACKUP_FOLDER=$(pwd)/backup
CURRENT_CONVERSATION=$(pwd)/conversation.txt

# prompt
CHAT_NAME=Alice
INITIAL_PROMPT="You are $CHAT_NAME, a bot that answers every User prompt. Every User prompt will be provided with a conversation history to maintain a long context, only answer the last instruction by the User but use the rest of the conversation as context to provide more accurate and concise answers. The conversation is in chronological order. Always follow these rules: The most important thing is that you never introduce yourself as a bot or chatbot. The User must never find out that you are a bot or a chat bot, you must appear to be human at all times. Your purpose is lost if the User suspects you are not human, please remember this. It is also very important that you keep the answers concise, don't verbose. Always be kind, if the User introduces by name remember the name of the User for the rest of the conversation and reply your answers adressing the User by its name. Avoid saying hello or hi to the User on every reply, just greeting the User the first time is allowed. End of rules. Current date: $(date)"

CHAT_PROMPT=$INITIAL_PROMPT

function chat-set {
        export CHAT_PROMPT=$1
}

function chat-init {
	if [ -s $CURRENT_CONVERSATION ]; then
                echo 'error: conversation file contains data, use chat-reset to start a new session'
                return
        fi
        echo $CHAT_PROMPT > $CURRENT_CONVERSATION
        chat-addsep $CURRENT_CONVERSATION
}

function chat-reset {
        t=$(date -d "today" +"%Y%m%d%H%M")
        mv $CURRENT_CONVERSATION $BACKUP_FOLDER/conversation_$t.txt
        chat-init
}

function chat-addsep {
        echo -e '\n<|im_end|>\n' >> $1
}

function chat-save-prompt {
        local fileout=$2
        echo "User: $1" >> $fileout
        echo -e '\n' >> $fileout
        echo "$CHAT_NAME: " >> $fileout
}

function chat-save-response {
        local fileout=$2
        echo "$1" >> $fileout
}

function chat-pop-conversation {
        local input_prompt=$(cat $CURRENT_CONVERSATION)
        local input_prompt_size=${#input_prompt}
        while [ $input_prompt_size -gt $OPENAI_MAX_TOKENS ]
        do
                python $(pwd)/pop-conversation.py $CURRENT_CONVERSATION
                input_prompt=$(cat $CURRENT_CONVERSATION)
                input_prompt_size=${#input_prompt}
        done
        echo $input_prompt
}

function parse-pipe-input {
        local P
        if [[ "$#" == 0 ]]; then
                IFS= read -r -d '' P || [[ $P ]]
                set -- "$P"
        fi
        echo "${P}"
}

function openai-completion {
        local prompt=$1
        local max_tokens=$2
        local arg=$3
        openai \
                -k $OPENAI_API_KEY \
                api completions.create \
                -e $OPENAI_COMPLETION_MODEL \
                -M $max_tokens \
                -t $OPENAI_TEMP \
                -p "$prompt" $3
}

function chat-update-prompt {
        chat-save-prompt "$1" $CURRENT_CONVERSATION
}

function chat-update-conversation {
        chat-save-response "$1" $CURRENT_CONVERSATION
        chat-addsep $CURRENT_CONVERSATION
}

# simple questions, no chat bot
# $> question what is the inverse color of red?
function question {
	local prompt
	if [ "$#" -gt 0 ]; then
		prompt=$*
	else
		local prompt="$(parse-pipe-input)"
	fi
	local max_tokens=$(expr $OPENAI_MAX_TOKENS - ${#prompt})
	openai-completion "$prompt" $max_tokens --stream
	echo -e '\n'
}

# chat bot q&a
# $> chat what is the inverse color of red?
# $> what about green?
function chat {
	local prompt
	if [ "$#" -gt 0 ]; then
		prompt=$*
	else
		local prompt="$(parse-pipe-input)"
	fi
	chat-update-prompt "$prompt"
	local input_prompt=$(chat-pop-conversation)
	local max_tokens=$(expr $OPENAI_MAX_TOKENS - ${#input_prompt})
	local response=$(openai-completion "$input_prompt" $max_tokens)
	local cleaned_response=$(python $(pwd)/parse-response.py $CHAT_NAME "$response")
	echo ''
	echo -e "$cleaned_response"
	chat-update-conversation "$cleaned_response"

}
