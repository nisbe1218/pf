from django.apps import AppConfig
import logging
import os

from .llm_client import get_llm_model_name


logger = logging.getLogger(__name__)


class PatientsConfig(AppConfig):
    name = 'patients'

    def ready(self):
        model_name = get_llm_model_name()
        logger.info('[LLM INIT] model = %s', model_name)
