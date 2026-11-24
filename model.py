from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import Ridge

MIN_RATINGS = 10


def _features(item):
    f = {
        "type=" + item.get("type", ""): 1,
        "genre=" + item.get("genre", "").strip().lower(): 1,
    }
    creator = (item.get("creator") or "").strip().lower()
    if creator:
        f["creator=" + creator] = 1
    if item.get("year"):
        f["year"] = (item["year"] - 2000) / 50
    if item.get("length"):
        scale = 1000 if item.get("type") == "book" else 100
        f["length"] = min(item["length"] / scale, 3)
    return f


def _avg_for(items, key, value):
    value = value.strip().lower()
    ratings = [i["rating"] for i in items if (i.get(key) or "").strip().lower() == value]
    if not ratings:
        return None, 0
    return sum(ratings) / len(ratings), len(ratings)


def predict_rating(items, new_item):
    n = len(items)
    if n < MIN_RATINGS:
        return {"locked": True, "count": n, "needed": MIN_RATINGS - n}

    ratings = [i["rating"] for i in items]
    mean = sum(ratings) / n

    vec = DictVectorizer()
    X = vec.fit_transform([_features(i) for i in items])
    model = Ridge(alpha=1.0).fit(X, [r - mean for r in ratings])
    raw = mean + float(model.predict(vec.transform([_features(new_item)]))[0])
    predicted = min(5.0, max(1.0, raw))

    reasons = []
    genre_avg, genre_n = _avg_for(items, "genre", new_item["genre"])
    if genre_n:
        reasons.append(f"You rate {new_item['genre']} {genre_avg:.1f} on average ({genre_n} rated).")
    else:
        reasons.append(
            f"You haven't rated any {new_item['genre']} yet, so this leans on your overall average of {mean:.1f}."
        )
    creator = (new_item.get("creator") or "").strip()
    if creator:
        c_avg, c_n = _avg_for(items, "creator", creator)
        if c_n:
            reasons.append(f"You rate {creator} {c_avg:.1f} on average ({c_n} rated).")

    confidence = "high" if genre_n >= 5 else "medium" if genre_n >= 2 else "low"
    return {
        "locked": False,
        "predicted": round(predicted, 1),
        "confidence": confidence,
        "reasons": reasons,
        "based_on": n,
    }