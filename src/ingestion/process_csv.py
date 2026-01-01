def row_to_text(row):
    return (
        f"Farmer {row['farmer_name']} from {row['location_state']}. "
        f"Soil Type: {row['soil_type']} (pH {row['soil_ph']}). "
        f"NPK Levels: N={row['nitrogen']} P={row['phosphorus']} K={row['potassium']}. "
        f"Weather: Rainfall {row['rainfall_mm']}mm Temp {row['temperature_c']}°C. "
        f"Recommended Crop: {row['recommended_crop']}. "
        f"Risk Level: {row['risk_level']}. "
        f"Cautions: {row['cautions']}."
    )

def prepare_documents(df):
    docs = []
    for _, row in df.iterrows():
        text = row_to_text(row)
        docs.append({
            "id": str(row["farmer_id"]),
            "text": text,
            "metadata": {
                "soil_type": row["soil_type"],
                "location_state": row["location_state"],
                "recommended_crop": row["recommended_crop"]
            }
        })
    return docs
