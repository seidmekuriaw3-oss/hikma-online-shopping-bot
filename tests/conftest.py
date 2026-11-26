import os

# Tests must not inherit production-mode validation or connect to a real database.
os.environ['ENVIRONMENT'] = 'test'
os.environ.setdefault(
	"DATABASE_URL",
	"postgresql://localhost/hikma_test",
)
