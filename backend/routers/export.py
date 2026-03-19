from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from session_store import get_session
import pandas as pd
import math
import numpy as np

router = APIRouter()

def clean_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    return obj

@router.get("/export/{session_id}")
def export_data(session_id: str):
    session = get_session(session_id)
    if not session or "df" not in session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    df = session["df"]
    if isinstance(df, (list, dict)):
        df = pd.DataFrame(df)
    
    records = df.to_dict(orient="records")
    return JSONResponse(content=clean_for_json({
        "data": records,
        "columns": df.columns.tolist(),
        "rows": len(df),
        "filename": session.get("filename", "unknown")
    }))

@router.get("/export/{session_id}/csv")
def export_csv(session_id: str):
    from fastapi.responses import StreamingResponse
    import io
    session = get_session(session_id)
    if not session or "df" not in session:
        raise HTTPException(status_code=404, detail="Session not found")
    df = session["df"]
    if isinstance(df, (list, dict)):
        df = pd.DataFrame(df)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    stream.seek(0)
    filename = session.get("filename", "export.csv")
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
