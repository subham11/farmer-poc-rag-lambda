def build_prompt(query, contexts):
    context_strings = []
    for ctx in contexts:
        context_strings.append(
            f"Crop: {ctx['metadata']['recommended_crop']} | "
            f"Soil: {ctx['metadata']['soil_type']} | "
            f"Location: {ctx['metadata']['location_state']}"
        )

    context_text = "\n".join(context_strings)

    return f"""
You are an agricultural assistant AI.
Use only the context below to answer the user's query.

Context:
{context_text}

Question:
{query}

Answer clearly and accurately:
"""
