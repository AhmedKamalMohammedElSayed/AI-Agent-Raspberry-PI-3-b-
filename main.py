import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from services import convert_audio_to_text, convert_text_to_speech, save_conversation
from rag_pipeline import RAGPipeline
from summarizer import ConversationSummarizer
import tempfile
from dotenv import load_dotenv
import os
from rag_config import USER_NAME, CONVERSATION_COUNT_THRESHOLD
from typing import Optional
from fastapi import Query

load_dotenv()
app = FastAPI(title="PerceptoAI RAG Pipeline")

@app.get("/")
async def root():
    return {"message": "PerceptoAI server is running!"}

@app.post("/process_audio")
async def process_audio(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    new_conv: Optional[bool] = Query(False, description="Start a new conversation"),
    voice: Optional[str] = Query("Sarah", description="Voice to use for the response")
):
    try:
        rag_pipeline = RAGPipeline(user_name=USER_NAME)
        conversation_summarizer = ConversationSummarizer(rag_pipeline)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            prompt = await convert_audio_to_text(temp_file.name)
            response = rag_pipeline.process_query(prompt)
            audio_response = await convert_text_to_speech(response["answer"], prompt, voice)
        
            conversation_count = save_conversation({
                "user_input": prompt,
                "ai_response": response,
                "embedder": rag_pipeline.embedder,
                "user_name": USER_NAME,
                "conv_count_threshold": CONVERSATION_COUNT_THRESHOLD
            }, new_conv)
            
            print("Number of conversations processed:", conversation_count)
            background_tasks.add_task(conversation_summarizer.process_conversation,
                                        conversation_count, CONVERSATION_COUNT_THRESHOLD)
        
        return {
                "transcription": prompt,
                "prompt_type": response["prompt_type"],
                "response": response["answer"],
                "audio_response": audio_response
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app)
