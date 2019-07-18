from rest_framework import routers

from .repository.views import RepositoryViewSet
from .repository.views import RepositoryVotesViewSet
from .repository.views import RepositoriesViewSet
from .repository.views import RepositoriesContributionsViewSet
from .examples.views import ExamplesViewSet
from .evaluate.views import EvaluateViewSet
from .evaluate.views import ResultsListViewSet
from .account.views import LoginViewSet


router = routers.SimpleRouter()
router.register('repository', RepositoryViewSet)
router.register('repository-votes', RepositoryVotesViewSet)
router.register('repositories', RepositoriesViewSet)
router.register('repositories-contributions', RepositoriesContributionsViewSet)
router.register('examples', ExamplesViewSet)
router.register('evaluate/results', ResultsListViewSet)
router.register('evaluate', EvaluateViewSet)
router.register('account/login', LoginViewSet)
