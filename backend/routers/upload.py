from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd
import io
import math
import threading
from session_store import create_session, update_session

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
        
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
            
        session_id = create_session()
        update_session(session_id, "df", df.where(pd.notnull(df), None).to_dict(orient="records"))
        update_session(session_id, "filename", file.filename)
        
        # Save to Supabase for Metabase visualization
        try:
            from db.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                rows = []
                df_for_upload = df.where(pd.notnull(df), None)
                for idx, row in df_for_upload.head(1000).iterrows():
                    rows.append({
                        "session_id": session_id,
                        "filename": file.filename,
                        "row_index": int(idx),
                        "data": row.to_dict()
                    })
                for i in range(0, len(rows), 100):
                    batch = rows[i:i+100]
                    supabase.table("uploaded_data").insert(batch).execute()
        except Exception as e:
            print(f"Supabase data upload failed (non-critical): {e}")
        
        # We trigger RAG indexing in the background asynchronously if needed 
        # (This avoids blocking the fast upload response)
        try:
            from rag.document_processor import process_and_index_dataframe
            # Using threading for a lightweight fire-and-forget
            threading.Thread(
                target=process_and_index_dataframe, 
                args=(df, file.filename, session_id)
            ).start()
        except ImportError:
            pass
            
        def clean_for_json(obj):
            import numpy as np
            if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [clean_for_json(i) for i in obj]
            return obj

        df_safe = df.where(pd.notnull(df), None)

        response_dict = {
            "session_id": session_id,
            "filename": file.filename,
            "rows": len(df),
            "columns": len(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample": df_safe.head(5).to_dict(orient="records"),
            "column_names": df.columns.tolist()
        }
        
        return clean_for_json(response_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
