from django.urls import path

from .views import PredictionPredictView, PredictionTrainView

urlpatterns = [
    path('predict/', PredictionPredictView.as_view(), name='prediction_predict'),
    path('train/', PredictionTrainView.as_view(), name='prediction_train'),
]
