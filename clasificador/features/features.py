# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

from threading import Thread

from progress.bar import Bar

import clasificador.features.distanciacategoria
from clasificador.features.feature import Feature
import clasificador.features.npersona
import clasificador.herramientas.chistesdotcom
from clasificador.herramientas.define import SUFIJO_PROGRESS_BAR
import clasificador.herramientas.persistencia
from clasificador.herramientas.reflection import cargar_modulos_vecinos, subclases

CANTIDAD_THREADS = 4


def abortar_si_feature_no_es_thread_safe(feature):
    assert CANTIDAD_THREADS == 1 or feature.thread_safe, \
        "La feature " + feature.nombre + " no es thread-safe y hay más de un hilo corriendo"


class Features:
    def __init__(self):
        self.bar = ""
        self.features = {}

        print("Comienzo de la carga de características")

        cargar_modulos_vecinos(__name__, __file__)

        for clase_feature in subclases(Feature):
            if clase_feature != clasificador.features.distanciacategoria.DistanciaCategoria \
                    and clase_feature != clasificador.features.npersona.NPersona:
                objeto_feature = clase_feature()
                if objeto_feature.incluir:
                    self.features[objeto_feature.nombre] = objeto_feature
                    print(objeto_feature.nombre)

        categorias_chistes_dot_com = clasificador.herramientas.chistesdotcom.obtener_categorias()

        for categoria in categorias_chistes_dot_com:
            feature = clasificador.features.distanciacategoria.DistanciaCategoria(categoria['id_clasificacion'],
                                                                                  categoria['nombre_clasificacion'],
                                                                                  False)
            if feature.incluir:
                self.features[feature.nombre] = feature
                print(feature.nombre)

        print("Fin de la carga de características")

    def calcular_features(self, tweets):
        Features.repartir_en_threads(self.calcular_features_thread, tweets)

    def calcular_feature(self, tweets, nombre_feature):
        Features.repartir_en_threads(self.calcular_feature_thread, tweets, nombre_feature)

    def calcular_features_faltantes(self, tweets):
        Features.repartir_en_threads(self.calcular_features_faltantes_thread, tweets)

    @staticmethod
    def repartir_en_threads(funcion, tweets, nombre_feature=None):
        intervalo = int(len(tweets) / CANTIDAD_THREADS)
        threads = []
        for i in range(CANTIDAD_THREADS - 1):
            if nombre_feature:
                args = (tweets[i * intervalo: (i + 1) * intervalo], nombre_feature, i)
            else:
                args = (tweets[i * intervalo: (i + 1) * intervalo], i)
            thread = Thread(target=funcion, args=args)
            threads.append(thread)

        if nombre_feature:
            args = (tweets[(CANTIDAD_THREADS - 1) * intervalo:], nombre_feature, CANTIDAD_THREADS - 1)
        else:
            args = (tweets[(CANTIDAD_THREADS - 1) * intervalo:], CANTIDAD_THREADS - 1)
        thread = Thread(target=funcion, args=args)
        threads.append(thread)

        for hilo in threads:
            hilo.start()

        for hilo in threads:
            hilo.join()

    def calcular_features_thread(self, tweets, identificador):
        if len(tweets) > 0:
            bar = Bar("Calculando features - " + str(identificador), max=len(tweets) * len(self.features),
                      suffix=SUFIJO_PROGRESS_BAR)
            bar.next(0)
            for tweet in tweets:
                for feature in list(self.features.values()):
                    abortar_si_feature_no_es_thread_safe(feature)
                    tweet.features[feature.nombre] = feature.calcular_feature(tweet)
                    bar.next()
            bar.finish()

    def calcular_feature_thread(self, tweets, nombre_feature, identificador):
        if len(tweets) > 0:
            bar = Bar("Calculando feature " + nombre_feature + ' - ' + str(identificador), max=len(tweets),
                      suffix=SUFIJO_PROGRESS_BAR)
            bar.next(0)
            feature = self.features[nombre_feature]
            abortar_si_feature_no_es_thread_safe(feature)
            for tweet in tweets:
                tweet.features[feature.nombre] = feature.calcular_feature(tweet)
                bar.next()
            bar.finish()

    def calcular_features_faltantes_thread(self, tweets, identificador):
        if len(tweets) > 0:
            bar = Bar("Calculando features - " + str(identificador), max=len(tweets) * len(self.features),
                      suffix=SUFIJO_PROGRESS_BAR)
            bar.next(0)
            for tweet in tweets:
                for feature in list(self.features.values()):
                    abortar_si_feature_no_es_thread_safe(feature)
                    if feature.nombre not in tweet.features:
                        tweet.features[feature.nombre] = feature.calcular_feature(tweet)
                    bar.next()
            bar.finish()
