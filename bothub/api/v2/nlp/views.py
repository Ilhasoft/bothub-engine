import base64
import json
import re
import requests

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

from rest_framework import mixins
from rest_framework import exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import AllowAny

from bothub.api.v2.repository.serializers import RepositorySerializer
from bothub.api.v2.nlp.serializers import NLPSerializer
from bothub.authentication.models import User
from bothub.common.models import RepositoryAuthorization
from bothub.common.models import RepositoryEntity
from bothub.common.models import RepositoryEvaluateResult
from bothub.common.models import RepositoryEvaluateResultScore
from bothub.common.models import RepositoryEvaluateResultIntent
from bothub.common.models import RepositoryEvaluateResultEntity
from bothub.common.models import RepositoryUpdate
from bothub.common.models import Repository
from bothub.common import languages
from bothub.utils import send_bot_data_file_aws


def check_auth(request):
    try:
        auth = request.META.get("HTTP_AUTHORIZATION").split()
        auth = auth[1]
        RepositoryAuthorization.objects.get(uuid=auth)
    except Exception:
        msg = _("Invalid token header.")
        raise exceptions.AuthenticationFailed(msg)


class RepositoryAuthorizationTrainViewSet(
    mixins.RetrieveModelMixin, mixins.CreateModelMixin, GenericViewSet
):
    queryset = RepositoryAuthorization.objects
    serializer_class = NLPSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        check_auth(request)
        repository_authorization = self.get_object()
        current_update = repository_authorization.repository.current_update(
            str(request.query_params.get("language"))
        )

        return Response(
            {
                "ready_for_train": current_update.ready_for_train,
                "current_update_id": current_update.id,
                "repository_authorization_user_id": repository_authorization.user.id,
                "language": current_update.language,
            }
        )

    @action(detail=True, methods=["POST"], url_name="start_training", lookup_field=[])
    def start_training(self, request, **kwargs):
        check_auth(request)

        repository = get_object_or_404(
            RepositoryUpdate, pk=request.data.get("update_id")
        )

        examples = [
            {"example_id": example.id, "example_intent": example.intent}
            for example in repository.examples
        ]

        repository.start_training(
            get_object_or_404(User, pk=request.data.get("by_user"))
        )

        label_examples_query = []

        for label_examples in (
            repository.examples.filter(entities__entity__label__isnull=False)
            .annotate(entities_count=models.Count("entities"))
            .filter(entities_count__gt=0)
        ):
            label_examples_query.append({"example_id": label_examples.id})

        return Response(
            {
                "language": repository.language,
                "update_id": repository.id,
                "repository_uuid": str(repository.repository.uuid),
                "examples": examples,
                "label_examples_query": label_examples_query,
                "intent": repository.intents,
                "algorithm": repository.algorithm,
                "use_name_entities": repository.use_name_entities,
                "use_competing_intents": repository.use_competing_intents,
                "ALGORITHM_STATISTICAL_MODEL": Repository.ALGORITHM_STATISTICAL_MODEL,
                "ALGORITHM_NEURAL_NETWORK_EXTERNAL": Repository.ALGORITHM_NEURAL_NETWORK_EXTERNAL,
            }
        )

    @action(detail=True, methods=["GET"], url_name="gettext", lookup_field=[])
    def get_text(self, request, **kwargs):
        check_auth(request)

        try:
            update_id = int(request.query_params.get("update_id"))
            example_id = int(request.query_params.get("example_id"))
        except ValueError:
            raise exceptions.NotFound()

        repository = get_object_or_404(
            get_object_or_404(RepositoryUpdate, pk=update_id).examples, pk=example_id
        ).get_text(request.query_params.get("language"))

        return Response({"get_text": repository})

    @action(detail=True, methods=["GET"], url_name="get_entities", lookup_field=[])
    def get_entities(self, request, **kwargs):
        check_auth(request)

        try:
            update_id = int(request.query_params.get("update_id"))
            example_id = int(request.query_params.get("example_id"))
        except ValueError:
            raise exceptions.NotFound()

        repository = get_object_or_404(
            get_object_or_404(RepositoryUpdate, pk=update_id).examples, pk=example_id
        ).get_entities(request.query_params.get("language"))

        entities = [entit.rasa_nlu_data for entit in repository]

        return Response({"entities": entities})

    @action(
        detail=True, methods=["GET"], url_name="get_entities_label", lookup_field=[]
    )
    def get_entities_label(self, request, **kwargs):
        check_auth(request)

        try:
            update_id = int(request.query_params.get("update_id"))
            example_id = int(request.query_params.get("example_id"))
        except ValueError:
            raise exceptions.NotFound()

        repository = get_object_or_404(
            get_object_or_404(RepositoryUpdate, pk=update_id).examples, pk=example_id
        ).get_entities(request.query_params.get("language"))

        entities = [
            example_entity.get_rasa_nlu_data(label_as_entity=True)
            for example_entity in filter(lambda ee: ee.entity.label, repository)
        ]

        return Response({"entities": entities})

    @action(detail=True, methods=["POST"], url_name="train_fail", lookup_field=[])
    def train_fail(self, request, **kwargs):
        check_auth(request)
        repository = get_object_or_404(
            RepositoryUpdate, pk=request.data.get("update_id")
        )
        repository.train_fail()
        return Response({})

    @action(detail=True, methods=["POST"], url_name="training_log", lookup_field=[])
    def training_log(self, request, **kwargs):
        check_auth(request)
        repository = get_object_or_404(
            RepositoryUpdate, pk=request.data.get("update_id")
        )
        repository.training_log = request.data.get("training_log")
        repository.save(update_fields=["training_log"])
        return Response({})


class RepositoryAuthorizationParseViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    queryset = RepositoryAuthorization.objects
    serializer_class = NLPSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        check_auth(request)
        repository_authorization = self.get_object()
        repository = repository_authorization.repository
        update = repository.last_trained_update(
            str(request.query_params.get("language"))
        )
        return Response(
            {
                "update": False if update is None else True,
                "update_id": update.id,
                "language": update.language,
            }
        )

    @action(detail=True, methods=["GET"], url_name="repository_entity", lookup_field=[])
    def repository_entity(self, request, **kwargs):
        check_auth(request)
        repository_update = get_object_or_404(
            RepositoryUpdate, pk=request.query_params.get("update_id")
        )
        repository_entity = get_object_or_404(
            RepositoryEntity,
            repository=repository_update.repository,
            value=request.query_params.get("entity"),
        )

        return Response(
            {
                "label": repository_entity.label,
                "label_value": repository_entity.label.value,
            }
        )


class RepositoryAuthorizationInfoViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    queryset = RepositoryAuthorization.objects
    serializer_class = NLPSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        check_auth(request)
        repository_authorization = self.get_object()
        repository = repository_authorization.repository
        serializer = RepositorySerializer(repository)
        return Response(serializer.data)


class RepositoryAuthorizationEvaluateViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    queryset = RepositoryAuthorization.objects
    serializer_class = NLPSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        check_auth(request)
        repository_authorization = self.get_object()
        repository = repository_authorization.repository
        update = repository.last_trained_update(
            str(request.query_params.get("language"))
        )
        return Response(
            {
                "update": False if update is None else True,
                "update_id": update.id,
                "language": update.language,
                "user_id": repository_authorization.user.id,
            }
        )

    @action(detail=True, methods=["GET"], url_name="evaluations", lookup_field=[])
    def evaluations(self, request, **kwargs):
        check_auth(request)
        repository_update = get_object_or_404(
            RepositoryUpdate, pk=request.query_params.get("update_id")
        )
        evaluations = repository_update.repository.evaluations(
            language=repository_update.language
        )

        data = []

        for evaluate in evaluations:
            entities = []

            for evaluate_entity in evaluate.get_entities(repository_update.language):
                entities.append(
                    {
                        "start": evaluate_entity.start,
                        "end": evaluate_entity.end,
                        "value": evaluate.text[
                            evaluate_entity.start : evaluate_entity.end
                        ],
                        "entity": evaluate_entity.entity.value,
                    }
                )

            data.append(
                {
                    "text": evaluate.get_text(repository_update.language),
                    "intent": evaluate.intent,
                    "entities": entities,
                }
            )
        return Response(data)

    @action(detail=True, methods=["POST"], url_name="evaluate_results", lookup_field=[])
    def evaluate_results(self, request, **kwargs):
        check_auth(request)
        repository_update = get_object_or_404(
            RepositoryUpdate, pk=request.data.get("update_id")
        )

        intents_score = RepositoryEvaluateResultScore.objects.create(
            precision=request.data.get("intentprecision"),
            f1_score=request.data.get("intentf1_score"),
            accuracy=request.data.get("intentaccuracy"),
        )

        entities_score = RepositoryEvaluateResultScore.objects.create(
            precision=request.data.get("entityprecision"),
            f1_score=request.data.get("entityf1_score"),
            accuracy=request.data.get("entityaccuracy"),
        )

        evaluate_result = RepositoryEvaluateResult.objects.create(
            repository_update=repository_update,
            entity_results=entities_score,
            intent_results=intents_score,
            matrix_chart=request.data.get("matrix_chart"),
            confidence_chart=request.data.get("confidence_chart"),
            log=json.dumps(request.data.get("log")),
        )

        return Response(
            {
                "evaluate_id": evaluate_result.id,
                "evaluate_version": evaluate_result.version,
            }
        )

    @action(
        detail=True,
        methods=["POST"],
        url_name="evaluate_results_intent",
        lookup_field=[],
    )
    def evaluate_results_intent(self, request, **kwargs):
        check_auth(request)

        evaluate_result = get_object_or_404(
            RepositoryEvaluateResult, pk=request.data.get("evaluate_id")
        )

        intent_score = RepositoryEvaluateResultScore.objects.create(
            precision=request.data.get("precision"),
            recall=request.data.get("recall"),
            f1_score=request.data.get("f1_score"),
            support=request.data.get("support"),
        )

        RepositoryEvaluateResultIntent.objects.create(
            intent=request.data.get("intent_key"),
            evaluate_result=evaluate_result,
            score=intent_score,
        )

        return Response({})

    @action(
        detail=True,
        methods=["POST"],
        url_name="evaluate_results_score",
        lookup_field=[],
    )
    def evaluate_results_score(self, request, **kwargs):
        check_auth(request)

        evaluate_result = get_object_or_404(
            RepositoryEvaluateResult, pk=request.data.get("evaluate_id")
        )

        repository_update = get_object_or_404(
            RepositoryUpdate, pk=request.data.get("update_id")
        )

        entity_score = RepositoryEvaluateResultScore.objects.create(
            precision=request.data.get("precision"),
            recall=request.data.get("recall"),
            f1_score=request.data.get("f1_score"),
            support=request.data.get("support"),
        )

        RepositoryEvaluateResultEntity.objects.create(
            entity=RepositoryEntity.objects.get(
                repository=repository_update.repository,
                value=request.data.get("entity_key"),
                create_entity=False,
            ),
            evaluate_result=evaluate_result,
            score=entity_score,
        )

        return Response({})


class NLPLangsViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = RepositoryAuthorization.objects
    serializer_class = NLPSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        return Response(
            {
                "english": [languages.LANGUAGE_EN],
                "portuguese": [languages.LANGUAGE_PT, languages.LANGUAGE_PT_BR],
                languages.LANGUAGE_PT: [languages.LANGUAGE_PT_BR],
                "pt-br": [languages.LANGUAGE_PT_BR],
                "br": [languages.LANGUAGE_PT_BR],
            }
        )


class RepositoryUpdateInterpretersViewSet(
    mixins.RetrieveModelMixin, mixins.CreateModelMixin, GenericViewSet
):
    queryset = RepositoryUpdate.objects
    serializer_class = NLPSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        check_auth(request)
        update = self.get_object()

        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|'
            r'[A-Z0-9-]{2,}\.?)|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if re.match(regex, update.bot_data) is not None:
            try:
                download = requests.get(update.bot_data)
                bot_data = base64.b64encode(download.content)
            except Exception:
                bot_data = b''
        else:
            bot_data = update.bot_data
        return Response({
            'update_id': update.id,
            'repository_uuid': update.repository.uuid,
            'bot_data': str(bot_data)
        })

    def create(self, request, *args, **kwargs):
        check_auth(request)
        id = request.data.get('id')
        repository = get_object_or_404(
            RepositoryUpdate,
            pk=id
        )
        if settings.AWS_SEND:
            bot_data = base64.b64decode(request.data.get('bot_data'))
            repository.save_training(
                send_bot_data_file_aws(
                    id,
                    bot_data
                )
            )
        else:
            repository.save_training(request.data.get('bot_data'))
        return Response({})
