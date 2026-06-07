## Maintenance

```bash
# Fix ownership after Docker writes files as root
sudo chown -R $USER:$USER ./data && chmod -R u+rwx ./data

# Reset Neo4j graph
docker compose run --rm app python main.py --reset-graph

# Query Neo4j directly
# Load .env to terminal
dos2unix .env # Fix windows to linux new line chars
export $(cat .env | xargs)
docker compose exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "MATCH (n) RETURN count(n);"
docker compose exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) RETURN n LIMIT 10;" > neo4jQueryResult.txt

docker compose logs neo4j

# Teardown
docker compose down
docker compose down -v
docker compose rm -s -f -v app
docker compose down --rmi all -v
```