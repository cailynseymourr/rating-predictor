# Rating Predictor

GitHub: https://github.com/cailynseymourr/rating-predictor
Canvas video: https://canvas.uoregon.edu/courses/291089/assignments/2121608/submissions/186448?download=25980555

A web app where you log the books and shows you've rated, and it predicts how much you'd like something new, with a short explanation of why.

## Tech stack
- Docker and Docker Compose (two containers: `web` and `mongo`)
- Python 3.12 and Flask 3.0.3 (REST API)
- MongoDB 7 (via PyMongo 4.8.0)
- scikit-learn 1.5.2 (ridge regression for predictions)
- Frontend: vanilla JavaScript with `fetch` (AJAX), HTML, and CSS, with no JS libraries
- Tests: pytest 8.3.3

## How to run locally
```
git clone https://github.com/cailynseymourr/rating-predictor.git
cd rating-predictor
docker-compose up --build
```
Then open http://localhost:5001. The app uses port 5001 on your machine (mapped to 5000 inside the container). MongoDB runs in its own container with a Docker volume for its data. No credentials or API keys are needed. `credentials.ini.sample` only holds placeholders.

**Using the predictor:** the database starts empty. Add at least 10 books or shows with your own ratings and the Predict card unlocks. Until then, a progress bar shows how many more are needed.

## How to run tests
With the app running (`docker-compose up`), in a second terminal:
```
docker-compose exec web python -m pytest -v
```
The tests use a separate `ratings_test` database, so they won't touch your real ratings.

## REST API
| Method | Route | Purpose |
|---|---|---|
| POST | `/api/items` | Create an item |
| GET | `/api/items` | List items (`?q=` search by title, `?type=`, `?genre=`) |
| GET | `/api/items/<id>` | Get one item |
| PUT | `/api/items/<id>` | Update an item |
| DELETE | `/api/items/<id>` | Delete an item |
| POST | `/api/predict` | Predict a rating for a new item |
| GET | `/api/model/stats` | Rating count and whether predictions are unlocked |
| GET | `/api/health` | Health check and Mongo connection status |

## Questions

### What is cool about your project?
Rating Predictor learns from your own taste. You log the books and shows you've finished and rate them, and once you have 10 ratings it predicts how much you'd like something new. What makes it different from a generic recommender is that every prediction explains itself, for example "You rate comedy 4.3 on average (6 rated)", along with a confidence level, so you can see why it guessed what it did. It's also honest about its limits: instead of making up predictions from nothing, it stays locked behind a progress bar ("7 more ratings until predictions unlock") until it has enough data.

### What AI tool(s) did you use, and for what specific tasks?
- **scikit-learn (model inference):** 'model.py' trains a ridge regression on the user's saved ratings each time a prediction is requested. The features are type, genre, creator, year, and length, and the model predicts how far a new item's rating will be from the user's average. If there isn't much data for a genre, the explanation says it's leaning on the overall average.
- **Claude (Anthropic):** I used Claude to choose help me choose the project idea, plan the work against the rubric, and debug code for the Flask API, the Docker setup, the frontend, the model, and the tests. I ran and tested everything myself and fixed the bugs we hit along the way.
- **Prompts I used:**
    - "I want to create a book or show rating predictor that logs what you've rated and predics how much you would like something new, can you create a to do and checklist for me for this project"
    - "What would be the best model for my predictor"
    - "When I tried testing my predictor it did not show up can you help me find the bug in my code?"
    - "What would be some important tests to have for my project"


### What did you learn by building the project?
The most useful thing I learned was how to build a machine learning model that works with very little data. My predictor is a ridge regression trained on the user's own ratings, which might be only 10 to a few dozen examples, so most of the work went into making it behave sensibly at that size. Genre, creator, and type are text, so I used scikit-learn's DictVectorizer to one-hot encode them, and I scaled year and length down so a year like 1965 couldn't overpower the other features. Instead of predicting a raw rating, the model predicts how far above or below the user's average a new item will land, and I clamp the result between 1 and 5 so it can never be an impossible rating. I chose ridge regression because, with so few examples and so many possible features (every creator is its own feature), a plain linear regression would memorize the data, and ridge's penalty on large weights keeps a single rating from swinging a prediction too far. I also learned that a number alone isn't enough: the app shows a confidence level based on how many items in that genre the user has rated, gives a plain-language reason like "You rate sci-fi 4.5 on average," and refuses to predict until there are 10 ratings, so deciding when not to predict became part of the model's design.

### What were the main technical challenges, and how did you solve them?
- Frontend bugs: After adding the Predict card, nothing appeared. The cause was two bugs: the HTML was nested wrongly, which put the card inside the wrong box, and I had defined the loadStats() function but never called it. I found both by reading through the files and fixed them.
- Cold start: A predictor with no data is meaningless, and I didn't want to fake it with sample ratings for books and shows I hadn't read. I solved this by locking predictions until there are 10 ratings and showing a progress bar, so the app is honest about what it knows.
- Port conflict: Docker failed because port 5000 was already in use on my machine. I fixed it by mapping the container's port 5000 to port 5001 in docker-compose.yml.