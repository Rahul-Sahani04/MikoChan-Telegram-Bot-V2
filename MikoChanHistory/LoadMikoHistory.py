import pickle
import json

# Load the pickle file
with open('MikoChanHistory/MikoChan.pkl', 'rb') as file:
    data = pickle.load(file)

print(data)
# Save the data as JSON
with open('MikoChanHistory/MikoChan.json', 'w') as file:
    json.dump(data, file)