from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from session_store import get_session
import pandas as pd
import numpy as np
import math
import time
import re
import sys
import os
import logging
from dotenv import load_dotenv

try:
    from db.supabase_client import get_supabase
    _supabase_available = True
except ImportError:
    _supabase_available = False

load_dotenv()

_streamlit_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "streamlit"))
if _streamlit_path not in sys.path:
    sys.path.insert(0, _streamlit_path)
from llm.client_factory import get_llm_response, GROQ_MODEL_LARGE

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    session_id: str
    question: str
    cross_dataset: bool = False


def clean_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, np.floating):
        if math.isnan(float(obj)) or math.isinf(float(obj)):
            return None
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    return obj


def _extract_code(llm_output: str) -> str:
    """Extract Python code from LLM response (handles markdown code blocks)."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()
    return llm_output.strip()


def _build_prompt(df: pd.DataFrame, question: str, prev_error: str | None = None) -> str:
    """Build the LLM prompt with data context and safety rules."""
    cols = df.columns.tolist()
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    sample_str = df.head(3).to_string(index=False)

    prompt = (
        "You are a pandas expert. Generate ONLY executable Python code "
        "with no explanation. The result must be stored in a variable called `result`.\n\n"
        "IMPORTANT RULES:\n"
        "- Never call .corr() or numeric operations on string/ID columns\n"
        "- Before any numeric operation, filter to numeric columns only:\n"
        "  numeric_df = df.select_dtypes(include='number')\n"
        "- Never assume a column is numeric — check dtype first\n"
        "- The variable `result` must be a string, number, or DataFrame\n"
        "- If result is a DataFrame, it will be converted to string automatically\n"
        "- Do NOT use print(), display(), st.write(), or show()\n"
        "- Do NOT import anything — pd, np, and df are already available\n"
        "- Keep code concise, max 15 lines\n\n"
        f"Question: {question}\n\n"
        f"DataFrame columns: {cols}\n"
        f"Numeric columns: {numeric_cols}\n"
        f"Categorical/string columns: {categorical_cols}\n"
        f"Column dtypes: {dtypes}\n"
        f"Sample data (first 3 rows):\n{sample_str}\n\n"
    )

    if prev_error:
        prompt += (
            f"PREVIOUS ATTEMPT FAILED with this error:\n{prev_error}\n"
            "Fix the code to avoid this error. Be extra careful with column types.\n\n"
        )

    prompt += "Return ONLY Python code. Store the answer in `result`."
    return prompt


def _exec_code(code: str, df: pd.DataFrame) -> str:
    """Execute generated code in a sandboxed environment and return result."""
    safe_builtins = {
        "len": len, "range": range, "str": str, "int": int, "float": float,
        "list": list, "dict": dict, "tuple": tuple, "set": set,
        "sorted": sorted, "enumerate": enumerate, "zip": zip,
        "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
        "isinstance": isinstance, "type": type, "True": True, "False": False,
        "None": None, "print": lambda *a, **k: None,  # swallow prints
    }
    local_vars = {"df": df.copy(), "pd": pd, "np": np}
    exec(code, {"__builtins__": safe_builtins}, local_vars)

    result = local_vars.get("result", local_vars.get("answer", None))
    if result is None:
        return "Code executed but no `result` variable was set."
    if isinstance(result, pd.DataFrame):
        return result.to_string(index=False)
    if isinstance(result, pd.Series):
        return result.to_string()
    return str(result)


def classify_query(question: str) -> str:
    question_lower = question.lower()
    if any(w in question_lower for w in ["trend", "over time", "growth", "change"]):
        return "trend"
    if any(w in question_lower for w in ["compare", "difference", "vs", "versus"]):
        return "comparison"
    if any(w in question_lower for w in ["filter", "where", "show me", "list"]):
        return "filter"
    if any(w in question_lower for w in ["average", "mean", "sum", "total", "count", "max", "min"]):
        return "aggregation"
    return "general"


def generate_follow_ups(question: str, answer: str, df_columns: list) -> list[str]:
    prompt = (
        f"Given this data question: '{question}'\n"
        f"And this answer: '{str(answer)[:200]}'\n"
        f"Available columns: {df_columns[:10]}\n"
        "Suggest exactly 3 short follow-up questions.\n"
        "Return ONLY a JSON array of 3 strings. No explanation."
    )
    try:
        response, _ = get_llm_response(
            prompt, temperature=0.7, max_tokens=200,
            groq_model=GROQ_MODEL_LARGE, module_name="nl_query_followups"
        )
        import json, re
        match = re.search(r"\[.*?\]", response, re.DOTALL)
        if match:
            return json.loads(match.group())[:3]
    except Exception:
        pass
    return [
        "What is the average of the main metric?",
        "Show me the top 5 records",
        "What are the trends over time?"
    ]


def generate_summary(question: str, answer: str) -> str:
    return f"Query analyzed: {question[:80]}. Result: {str(answer)[:150]}."


@router.post("/query")
def run_query(req: QueryRequest):
    session = get_session(req.session_id)
    if not session or "df" not in session:
        raise HTTPException(status_code=404, detail="Session or DataFrame not found")

    df = session["df"]
    if isinstance(df, (list, dict)):
        df = pd.DataFrame(df)
    query_type = classify_query(req.question)
    start_time = time.time()
    code = ""

    try:
        # First attempt
        prompt = _build_prompt(df, req.question)
        llm_text, _ = get_llm_response(
            prompt, temperature=0.1, max_tokens=800,
            groq_model=GROQ_MODEL_LARGE, module_name="nl_query"
        )
        code = _extract_code(llm_text)

        try:
            answer = _exec_code(code, df)
        except Exception as exec_err:
            # Retry with error context
            logger.warning("NL Query first attempt failed: %s — retrying", exec_err)
            retry_prompt = _build_prompt(df, req.question, prev_error=str(exec_err))
            retry_text, _ = get_llm_response(
                retry_prompt, temperature=0.1, max_tokens=800,
                groq_model=GROQ_MODEL_LARGE, module_name="nl_query_retry"
            )
            code = _extract_code(retry_text)
            try:
                answer = _exec_code(code, df)
            except Exception as retry_err:
                answer = f"Query could not be executed after retry. Error: {str(retry_err)}"

        execution_time_ms = int((time.time() - start_time) * 1000)
        summary = generate_summary(req.question, answer)
        follow_ups = generate_follow_ups(req.question, answer, df.columns.tolist())

        if _supabase_available:
            supabase = get_supabase()
            if supabase:
                try:
                    supabase.table("nl_query_history").insert({
                        "session_id": req.session_id,
                        "question": req.question,
                        "answer": str(answer)[:500],
                        "query_type": query_type,
                        "summary": summary,
                        "follow_ups": follow_ups,
                        "execution_time_ms": execution_time_ms,
                        "success": True,
                    }).execute()
                except Exception as e:
                    logger.warning(f"Failed to store query history: {e}")

        return clean_for_json({
            "question": req.question,
            "answer": answer,
            "code_used": code,
            "execution_time_ms": execution_time_ms,
            "query_type": query_type,
            "summary": summary,
            "follow_ups": follow_ups,
        })

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return clean_for_json({
            "question": req.question,
            "answer": f"Error: {str(e)}",
            "code_used": code,
            "execution_time_ms": execution_time_ms,
            "query_type": query_type,
            "summary": generate_summary(req.question, f"Error: {str(e)}"),
            "follow_ups": generate_follow_ups(req.question, f"Error: {str(e)}", df.columns.tolist()),
        })
