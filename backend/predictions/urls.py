from django.urls import path

from .views import (
    PredictionPredictView,
    PredictionTrainView,
    PredictionHistoryView,
    PredictionMetricsView
)

urlpatterns = [
    # 🔮 Prédiction
    path('predict/', PredictionPredictView.as_view(), name='prediction_predict'),

    # 🧠 Entraînement modèles
    path('train/', PredictionTrainView.as_view(), name='prediction_train'),

    # 📊 Historique des prédictions
    path('history/', PredictionHistoryView.as_view(), name='prediction_history'),

    # 📈 Métriques modèles ML
    path('metrics/', PredictionMetricsView.as_view(), name='prediction_metrics'),
]