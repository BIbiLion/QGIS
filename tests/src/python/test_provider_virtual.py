# -*- coding: utf-8 -*-
"""QGIS Unit tests for QgsVirtualLayerProvider

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
__author__ = 'Hugo Mercier'
__date__ = '26/11/2015'
__copyright__ = 'Copyright 2015, The QGIS Project'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import qgis
import os
import tempfile
import sys

from qgis.core import (QGis,
                       QgsVectorLayer,
                       QgsFeature,
                       QgsFeatureRequest,
                       QgsField,
                       QgsGeometry,
                       QgsPoint,
                       QgsMapLayerRegistry,
                       QgsRectangle,
                       QgsErrorMessage,
                       QgsProviderRegistry,
                       QgsVirtualLayerDefinition,
                       QgsWKBTypes,
                       QgsProject
                       )

from utilities import (unitTestDataPath,
                       getQgisTestApp,
                       TestCase,
                       unittest
                       )
from providertestbase import ProviderTestCase
from PyQt4.QtCore import *

try:
    from pyspatialite import dbapi2 as sqlite3
except ImportError:
    print "You should install pyspatialite to run the tests"
    raise ImportError

import tempfile

# Convenience instances in case you may need them
QGISAPP, CANVAS, IFACE, PARENT = getQgisTestApp()
TEST_DATA_DIR = unitTestDataPath()


class TestQgsVirtualLayerProvider(TestCase, ProviderTestCase):

    @classmethod
    def setUpClass(cls):
        """Run before all tests"""
        # Create the layer for the common provider tests
        shp = os.path.join(TEST_DATA_DIR, 'provider/shapefile.shp')
        d = QgsVirtualLayerDefinition()
        d.addSource("vtab1", shp, "ogr")
        d.setUid("pk")
        cls.vl = QgsVectorLayer(d.toString(), u'test', u'virtual')
        assert (cls.vl.isValid())
        cls.provider = cls.vl.dataProvider()

    @classmethod
    def tearDownClass(cls):
        """Run after all tests"""
        pass

    def setUp(self):
        """Run before each test."""
        self.testDataDir = unitTestDataPath()
        print "****************************************************"
        print "In method", self._testMethodName
        print "****************************************************"
        pass

    def tearDown(self):
        """Run after each test."""
        pass

    def test_CsvNoGeometry(self):
        l1 = QgsVectorLayer(QUrl.fromLocalFile(os.path.join(self.testDataDir, "delimitedtext/test.csv")).toString() + "?type=csv&geomType=none&subsetIndex=no&watchFile=no", "test", "delimitedtext", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        l2 = QgsVectorLayer("?layer_ref=" + l1.id(), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)

        QgsMapLayerRegistry.instance().removeMapLayer(l1.id())

    def test_source_escaping(self):
        # the source contains ':'
        source = QUrl.fromLocalFile(os.path.join(self.testDataDir, "delimitedtext/test.csv")).toString() + "?type=csv&geomType=none&subsetIndex=no&watchFile=no"
        d = QgsVirtualLayerDefinition()
        d.addSource("t", source, "delimitedtext")
        l = QgsVectorLayer(d.toString(), "vtab", "virtual", False)
        self.assertEqual(l.isValid(), True)

    def test_source_escaping2(self):
        def create_test_db(dbfile):
            if os.path.exists(dbfile):
                os.remove(dbfile)
            con = sqlite3.connect(dbfile)
            cur = con.cursor()
            cur.execute("SELECT InitSpatialMetadata(1)")
            cur.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            cur.execute("SELECT AddGeometryColumn('test', 'geometry', 4326, 'POINT', 'XY')")
            sql = "INSERT INTO test (id, name, geometry) "
            sql += "VALUES (1, 'toto',GeomFromText('POINT(0 0)',4326))"
            cur.execute(sql)
            con.close()

        # the source contains ',' and single quotes
        fn = os.path.join(tempfile.gettempdir(), "test,.db")
        create_test_db(fn)
        source = "dbname='%s' table=\"test\" (geometry) sql=" % fn
        d = QgsVirtualLayerDefinition()
        d.addSource("t", source, "spatialite")
        l = QgsVectorLayer(d.toString(), "vtab", "virtual", False)
        self.assertEqual(l.isValid(), True)

        # the source contains ':' and single quotes
        fn = os.path.join(tempfile.gettempdir(), "test:.db")
        create_test_db(fn)
        source = "dbname='%s' table=\"test\" (geometry) sql=" % fn
        d = QgsVirtualLayerDefinition()
        d.addSource("t", source, "spatialite")
        l = QgsVectorLayer(d.toString(), "vtab", "virtual", False)
        self.assertEqual(l.isValid(), True)

    def test_DynamicGeometry(self):
        l1 = QgsVectorLayer(QUrl.fromLocalFile(os.path.join(self.testDataDir, "delimitedtext/testextpt.txt")).toString() + "?type=csv&delimiter=%7C&geomType=none&subsetIndex=no&watchFile=no", "test", "delimitedtext", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        query = QUrl.toPercentEncoding("select *,makepoint(x,y) as geom from vtab1")
        l2 = QgsVectorLayer("?layer_ref=%s&query=%s&geometry=geom:point:0&uid=id" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)

        QgsMapLayerRegistry.instance().removeMapLayer(l1)

    def test_ShapefileWithGeometry(self):
        l1 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "france_parts", "ogr", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        # use a temporary file
        l2 = QgsVectorLayer("?layer_ref=" + l1.id(), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)

        l2 = QgsVectorLayer("?layer_ref=%s:nn" % l1.id(), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)

        QgsMapLayerRegistry.instance().removeMapLayer(l1.id())

    def test_Query(self):
        l1 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "france_parts", "ogr", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)
        ref_sum = sum(f.attributes()[0] for f in l1.getFeatures())

        query = QUrl.toPercentEncoding("SELECT * FROM vtab1")
        l2 = QgsVectorLayer("?layer_ref=%s&geometry=geometry:3:4326&query=%s&uid=OBJECTID" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 3)

        ref_sum2 = sum(f.attributes()[0] for f in l2.getFeatures())
        ref_sum3 = sum(f.id() for f in l2.getFeatures())
        # check we have the same rows
        self.assertEqual(ref_sum, ref_sum2)
        # check the id is ok
        self.assertEqual(ref_sum, ref_sum3)

        # the same, without specifying the geometry column name
        l2 = QgsVectorLayer("?layer_ref=%s&query=%s&uid=OBJECTID" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 3)
        ref_sum2 = sum(f.attributes()[0] for f in l2.getFeatures())
        ref_sum3 = sum(f.id() for f in l2.getFeatures())
        # check we have the same rows
        self.assertEqual(ref_sum, ref_sum2)
        # check the id is ok
        self.assertEqual(ref_sum, ref_sum3)

        # with two geometry columns
        query = QUrl.toPercentEncoding("SELECT *,geometry as geom FROM vtab1")
        l2 = QgsVectorLayer("?layer_ref=%s&query=%s&uid=OBJECTID&geometry=geom:3:4326" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 3)
        ref_sum2 = sum(f.attributes()[0] for f in l2.getFeatures())
        ref_sum3 = sum(f.id() for f in l2.getFeatures())
        # check we have the same rows
        self.assertEqual(ref_sum, ref_sum2)
        # check the id is ok
        self.assertEqual(ref_sum, ref_sum3)

        # with two geometry columns, but no geometry column specified (will take the first)
        l2 = QgsVectorLayer("?layer_ref=%s&query=%s&uid=OBJECTID" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 3)
        ref_sum2 = sum(f.attributes()[0] for f in l2.getFeatures())
        ref_sum3 = sum(f.id() for f in l2.getFeatures())
        # check we have the same rows
        self.assertEqual(ref_sum, ref_sum2)
        # check the id is ok
        self.assertEqual(ref_sum, ref_sum3)

        # the same, without geometry
        query = QUrl.toPercentEncoding("SELECT * FROM ww")
        l2 = QgsVectorLayer("?layer_ref=%s:ww&query=%s&uid=ObJeCtId&nogeometry" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 100) # NoGeometry
        ref_sum2 = sum(f.attributes()[0] for f in l2.getFeatures())
        ref_sum3 = sum(f.id() for f in l2.getFeatures())
        self.assertEqual(ref_sum, ref_sum2)
        self.assertEqual(ref_sum, ref_sum3)

        # check that it fails when a query has a wrong geometry column
        l2 = QgsVectorLayer("?layer_ref=%s&query=%s&geometry=geo" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), False)

        QgsMapLayerRegistry.instance().removeMapLayer(l1.id())

    def test_QueryUrlEncoding(self):
        l1 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "france_parts", "ogr", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        query = str(QUrl.toPercentEncoding("SELECT * FROM vtab1"))
        l2 = QgsVectorLayer("?layer_ref=%s&query=%s&uid=ObjectId&nogeometry" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)

        QgsMapLayerRegistry.instance().removeMapLayer(l1.id())

    def test_QueryTableName(self):
        l1 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "france_parts", "ogr", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        query = str(QUrl.toPercentEncoding("SELECT * FROM vt"))
        l2 = QgsVectorLayer("?layer_ref=%s:vt&query=%s&uid=ObJeCtId&nogeometry" % (l1.id(), query), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 100) # NoGeometry

        QgsMapLayerRegistry.instance().removeMapLayer(l1.id())

    def test_Join(self):
        l1 = QgsVectorLayer(os.path.join(self.testDataDir, "points.shp"), "points", "ogr", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)
        l2 = QgsVectorLayer(os.path.join(self.testDataDir, "points_relations.shp"), "points_relations", "ogr", False)
        self.assertEqual(l2.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l2)
        ref_sum = sum(f.attributes()[1] for f in l2.getFeatures())

        # use a temporary file
        query = QUrl.toPercentEncoding("select id,Pilots,vtab1.geometry from vtab1,vtab2 where intersects(vtab1.geometry,vtab2.geometry)")
        l3 = QgsVectorLayer("?layer_ref=%s&layer_ref=%s&uid=id&query=%s&geometry=geometry:1:4326" % (l1.id(), l2.id(), query), "vtab", "virtual", False)
        self.assertEqual(l3.isValid(), True)
        self.assertEqual(l3.dataProvider().geometryType(), 1)
        self.assertEqual(l3.dataProvider().fields().count(), 2)
        ref_sum2 = sum(f.id() for f in l3.getFeatures())
        self.assertEqual(ref_sum, ref_sum2)

        QgsMapLayerRegistry.instance().removeMapLayer(l1)
        QgsMapLayerRegistry.instance().removeMapLayer(l2)

    def test_geometryTypes(self):

        geo = [(1, "POINT", "(0 0)"),
               (2, "LINESTRING", "(0 0,1 0)"),
               (3, "POLYGON", "((0 0,1 0,1 1,0 0))"),
               (4, "MULTIPOINT", "((1 1))"),
               (5, "MULTILINESTRING", "((0 0,1 0),(0 1,1 1))"),
               (6, "MULTIPOLYGON", "(((0 0,1 0,1 1,0 0)),((2 2,3 0,3 3,2 2)))")]
        for wkb_type, wkt_type, wkt in geo:
            l = QgsVectorLayer("%s?crs=epsg:4326" % wkt_type, "m1", "memory", False)
            self.assertEqual(l.isValid(), True)
            QgsMapLayerRegistry.instance().addMapLayer(l)

            f1 = QgsFeature(1)
            g = QgsGeometry.fromWkt(wkt_type + wkt)
            self.assertEqual(g is None, False)
            f1.setGeometry(g)
            l.dataProvider().addFeatures([f1])

            l2 = QgsVectorLayer("?layer_ref=%s" % l.id(), "vtab", "virtual", False)
            self.assertEqual(l2.isValid(), True)
            self.assertEqual(l2.dataProvider().featureCount(), 1)
            self.assertEqual(l2.dataProvider().geometryType(), wkb_type)

            QgsMapLayerRegistry.instance().removeMapLayer(l.id())

    def test_embeddedLayer(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))
        l = QgsVectorLayer("?layer=ogr:%s" % source, "vtab", "virtual", False)
        self.assertEqual(l.isValid(), True)

        l = QgsVectorLayer("?layer=ogr:%s:nn" % source, "vtab", "virtual", False)
        self.assertEqual(l.isValid(), True)

    def test_filter_rect(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))

        query = QUrl.toPercentEncoding("select * from vtab where _search_frame_=BuildMbr(-2.10,49.38,-1.3,49.99,4326)")
        l2 = QgsVectorLayer("?layer=ogr:%s:vtab&query=%s&uid=objectid" % (source, query), "vtab2", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().featureCount(), 1)
        a = [fit.attributes()[4] for fit in l2.getFeatures()]
        self.assertEqual(a, [u"Basse-Normandie"])

    def test_recursiveLayer(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))
        l = QgsVectorLayer("?layer=ogr:%s" % source, "vtab", "virtual", False)
        self.assertEqual(l.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l)

        l2 = QgsVectorLayer("?layer_ref=" + l.id(), "vtab2", "virtual", False)
        self.assertEqual(l2.isValid(), True)

        QgsMapLayerRegistry.instance().removeMapLayer(l.id())

    def test_no_geometry(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))
        df = QgsVirtualLayerDefinition()
        df.addSource("vtab", os.path.join(self.testDataDir, "france_parts.shp"), "ogr")
        df.setGeometryWkbType(QgsWKBTypes.NoGeometry)
        l2 = QgsVectorLayer(df.toString(), "vtab2", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 100) # NoGeometry

    def test_reopen(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))
        tmp = QUrl.fromLocalFile(os.path.join(tempfile.gettempdir(), "t.sqlite")).toString()
        l = QgsVectorLayer("%s?layer=ogr:%s:vtab" % (tmp, source), "vtab2", "virtual", False)
        self.assertEqual(l.isValid(), True)

        l2 = QgsVectorLayer(tmp, "tt", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 3)
        self.assertEqual(l2.dataProvider().featureCount(), 4)

    def test_reopen2(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))
        tmp = QUrl.fromLocalFile(os.path.join(tempfile.gettempdir(), "t.sqlite")).toString()
        l = QgsVectorLayer("%s?layer=ogr:%s:vtab&nogeometry" % (tmp, source), "vtab2", "virtual", False)
        self.assertEqual(l.isValid(), True)

        l2 = QgsVectorLayer(tmp, "tt", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 100)
        self.assertEqual(l2.dataProvider().featureCount(), 4)

    def test_reopen3(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))
        tmp = QUrl.fromLocalFile(os.path.join(tempfile.gettempdir(), "t.sqlite")).toString()
        query = QUrl.toPercentEncoding("SELECT * FROM vtab")
        l = QgsVectorLayer("%s?layer=ogr:%s:vtab&query=%s&uid=objectid&geometry=geometry:3:4326" % (tmp, source, query), "vtab2", "virtual", False)
        self.assertEqual(l.isValid(), True)

        l2 = QgsVectorLayer(tmp, "tt", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 3)
        self.assertEqual(l2.dataProvider().featureCount(), 4)
        sumid = sum([f.id() for f in l2.getFeatures()])
        self.assertEqual(sumid, 10659)
        suma = sum([f.attributes()[1] for f in l2.getFeatures()])
        self.assertEqual(suma, 3064.0)

    def test_reopen4(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))
        tmp = QUrl.fromLocalFile(os.path.join(tempfile.gettempdir(), "t.sqlite")).toString()
        query = QUrl.toPercentEncoding("SELECT * FROM vtab")
        l = QgsVectorLayer("%s?layer=ogr:%s:vtab&query=%s&uid=objectid&nogeometry" % (tmp, source, query), "vtab2", "virtual", False)
        self.assertEqual(l.isValid(), True)

        l2 = QgsVectorLayer(tmp, "tt", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        self.assertEqual(l2.dataProvider().geometryType(), 100)
        self.assertEqual(l2.dataProvider().featureCount(), 4)
        sumid = sum([f.id() for f in l2.getFeatures()])
        self.assertEqual(sumid, 10659)
        suma = sum([f.attributes()[1] for f in l2.getFeatures()])
        self.assertEqual(suma, 3064.0)

    def test_refLayer(self):
        l1 = QgsVectorLayer(QUrl.fromLocalFile(os.path.join(self.testDataDir, "delimitedtext/test.csv")).toString() + "?type=csv&geomType=none&subsetIndex=no&watchFile=no", "test", "delimitedtext", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        l2 = QgsVectorLayer("?layer_ref=" + l1.id(), "vtab", "virtual", False)
        self.assertEqual(l2.isValid(), True)

        # now delete the layer
        QgsMapLayerRegistry.instance().removeMapLayer(l1.id())
        # check that it does not crash
        print sum([f.id() for f in l2.getFeatures()])

    def test_refLayers(self):
        l1 = QgsVectorLayer(QUrl.fromLocalFile(os.path.join(self.testDataDir, "delimitedtext/test.csv")).toString() + "?type=csv&geomType=none&subsetIndex=no&watchFile=no", "test", "delimitedtext", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        # cf qgis bug #12266
        for i in range(10):
            q = QUrl.toPercentEncoding("select * from t" + str(i))
            l2 = QgsVectorLayer("?layer_ref=%s:t%d&query=%s&uid=id" % (l1.id(), i, q), "vtab", "virtual", False)
            QgsMapLayerRegistry.instance().addMapLayer(l2)
            self.assertEqual(l2.isValid(), True)
            s = sum([f.id() for f in l2.dataProvider().getFeatures()])
            self.assertEqual(sum([f.id() for f in l2.getFeatures()]), 21)
            QgsMapLayerRegistry.instance().removeMapLayer(l2.id())

    def test_refLayers2(self):
        l1 = QgsVectorLayer(QUrl.fromLocalFile(os.path.join(self.testDataDir, "delimitedtext/test.csv")).toString() + "?type=csv&geomType=none&subsetIndex=no&watchFile=no", "test", "delimitedtext", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        # referenced layers cannot be stored !
        tmp = QUrl.fromLocalFile(os.path.join(tempfile.gettempdir(), "t.sqlite")).toString()
        l2 = QgsVectorLayer("%s?layer_ref=%s" % (tmp, l1.id()), "tt", "virtual", False)
        self.assertEqual(l2.isValid(), False)
        self.assertEqual("Cannot store referenced layers" in l2.dataProvider().error().message(), True)

    def test_sql(self):
        l1 = QgsVectorLayer(QUrl.fromLocalFile(os.path.join(self.testDataDir, "delimitedtext/test.csv")).toString() + "?type=csv&geomType=none&subsetIndex=no&watchFile=no", "test", "delimitedtext", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        l3 = QgsVectorLayer("?query=SELECT * FROM test", "tt", "virtual")

        self.assertEqual(l3.isValid(), True)
        s = sum(f.id() for f in l3.getFeatures())
        self.assertEqual(s, 15)

    def test_sql2(self):
        l2 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "france_parts", "ogr", False)
        self.assertEqual(l2.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l2)

        query = QUrl.toPercentEncoding("SELECT * FROM france_parts")
        l4 = QgsVectorLayer("?query=%s" % query, "tt", "virtual")
        self.assertEqual(l4.isValid(), True)

        self.assertEqual(l4.dataProvider().geometryType(), 3)
        self.assertEqual(l4.dataProvider().crs().postgisSrid(), 4326)

        n = 0
        r = QgsFeatureRequest(QgsRectangle(-1.677, 49.624, -0.816, 49.086))
        for f in l4.getFeatures(r):
            self.assertEqual(f.geometry() is not None, True)
            self.assertEqual(f.attributes()[0], 2661)
            n += 1
        self.assertEqual(n, 1)

        # use uid
        query = QUrl.toPercentEncoding("SELECT * FROM france_parts")
        l5 = QgsVectorLayer("?query=%s&geometry=geometry:polygon:4326&uid=ObjectId" % query, "tt", "virtual")
        self.assertEqual(l5.isValid(), True)

        idSum = sum(f.id() for f in l5.getFeatures())
        self.assertEqual(idSum, 10659)

        r = QgsFeatureRequest(2661)
        idSum2 = sum(f.id() for f in l5.getFeatures(r))
        self.assertEqual(idSum2, 2661)

        r = QgsFeatureRequest()
        r.setFilterFids([2661, 2664])
        self.assertEqual(sum(f.id() for f in l5.getFeatures(r)), 2661 + 2664)

        # test attribute subset
        r = QgsFeatureRequest()
        r.setFlags(QgsFeatureRequest.SubsetOfAttributes)
        r.setSubsetOfAttributes([1])
        s = [(f.id(), f.attributes()[1]) for f in l5.getFeatures(r)]
        self.assertEqual(sum(map(lambda x: x[0], s)), 10659)
        self.assertEqual(sum(map(lambda x: x[1], s)), 3064.0)

        # test NoGeometry
        # by request flag
        r = QgsFeatureRequest()
        r.setFlags(QgsFeatureRequest.NoGeometry)
        self.assertEqual(all([f.geometry() is None for f in l5.getFeatures(r)]), True)

        # test subset
        self.assertEqual(l5.dataProvider().featureCount(), 4)
        l5.setSubsetString("ObjectId = 2661")
        idSum2 = sum(f.id() for f in l5.getFeatures(r))
        self.assertEqual(idSum2, 2661)
        self.assertEqual(l5.dataProvider().featureCount(), 1)

    def test_sql3(self):
        l2 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "france_parts", "ogr", False)
        self.assertEqual(l2.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l2)

        # unnamed column
        query = QUrl.toPercentEncoding("SELECT 42")
        l4 = QgsVectorLayer("?query=%s" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), False)
        self.assertEqual("Result column #1 has no name" in l4.dataProvider().error().message(), True)

    def test_sql_field_types(self):
        query = QUrl.toPercentEncoding("SELECT 42 as t, 'ok'||'ok' as t2, GeomFromText('') as t3, 3.14*2 as t4")
        l4 = QgsVectorLayer("?query=%s" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        self.assertEqual(l4.dataProvider().fields().at(0).name(), "t")
        self.assertEqual(l4.dataProvider().fields().at(0).type(), QVariant.Int)
        self.assertEqual(l4.dataProvider().fields().at(1).name(), "t2")
        self.assertEqual(l4.dataProvider().fields().at(1).type(), QVariant.String)
        self.assertEqual(l4.dataProvider().fields().at(2).name(), "t3")
        self.assertEqual(l4.dataProvider().fields().at(2).type(), QVariant.String)
        self.assertEqual(l4.dataProvider().fields().at(3).name(), "t4")
        self.assertEqual(l4.dataProvider().fields().at(3).type(), QVariant.Double)

        # with type annotations
        query = QUrl.toPercentEncoding("SELECT '42.0' as t /*:real*/, 3 as t2/*:text  */, GeomFromText('') as t3 /*:multiPoInT:4326 */, 3.14*2 as t4/*:int*/")
        l4 = QgsVectorLayer("?query=%s" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        self.assertEqual(l4.dataProvider().fields().at(0).name(), "t")
        self.assertEqual(l4.dataProvider().fields().at(0).type(), QVariant.Double)
        self.assertEqual(l4.dataProvider().fields().at(1).name(), "t2")
        self.assertEqual(l4.dataProvider().fields().at(1).type(), QVariant.String)
        self.assertEqual(l4.dataProvider().fields().at(2).name(), "t4")
        self.assertEqual(l4.dataProvider().fields().at(2).type(), QVariant.Int)
        self.assertEqual(l4.dataProvider().geometryType(), 4) # multipoint

        # test value types (!= from declared column types)
        for f in l4.getFeatures():
            self.assertEqual(f.attributes()[0], "42.0")
            self.assertEqual(f.attributes()[1], 3)
            self.assertEqual(f.attributes()[2], 6.28)

        # with type annotations and url options
        query = QUrl.toPercentEncoding("SELECT 1 as id /*:int*/, geomfromtext('point(0 0)',4326) as geometry/*:point:4326*/")
        l4 = QgsVectorLayer("?query=%s&geometry=geometry" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        self.assertEqual(l4.dataProvider().geometryType(), 1) # point

        # with type annotations and url options (2)
        query = QUrl.toPercentEncoding("SELECT 1 as id /*:int*/, 3.14 as f, geomfromtext('point(0 0)',4326) as geometry/*:point:4326*/")
        l4 = QgsVectorLayer("?query=%s&geometry=geometry&field=id:text" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        self.assertEqual(l4.dataProvider().fields().at(0).name(), "id")
        self.assertEqual(l4.dataProvider().fields().at(0).type(), QVariant.String)
        self.assertEqual(l4.dataProvider().fields().at(1).name(), "f")
        self.assertEqual(l4.dataProvider().fields().at(1).type(), QVariant.Double)
        self.assertEqual(l4.dataProvider().geometryType(), 1) # point

    def test_sql3b(self):
        query = QUrl.toPercentEncoding("SELECT GeomFromText('POINT(0 0)') as geom")
        l4 = QgsVectorLayer("?query=%s&geometry=geom" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        self.assertEqual(l4.dataProvider().geometryType(), 1)

        # forced geometry type
        query = QUrl.toPercentEncoding("SELECT GeomFromText('POINT(0 0)') as geom")
        l4 = QgsVectorLayer("?query=%s&geometry=geom:point:0" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        self.assertEqual(l4.dataProvider().geometryType(), 1)

        query = QUrl.toPercentEncoding("SELECT CastToPoint(GeomFromText('POINT(0 0)')) as geom")
        l4 = QgsVectorLayer("?query=%s" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        self.assertEqual(l4.dataProvider().geometryType(), 1)

    def test_sql4(self):
        l2 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "france_parts", "ogr", False)
        self.assertEqual(l2.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l2)

        query = QUrl.toPercentEncoding("SELECT OBJECTId from france_parts")
        l4 = QgsVectorLayer("?query=%s" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        s = sum(f.attributes()[0] for f in l4.getFeatures())
        self.assertEqual(s, 10659)

    def test_layer_name(self):
        # test space and upper case
        l2 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "FranCe parts", "ogr", False)
        self.assertEqual(l2.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l2)

        query = QUrl.toPercentEncoding('SELECT OBJECTId from "FranCe parts"')
        l4 = QgsVectorLayer("?query=%s" % query, "tt", "virtual", False)
        self.assertEqual(l4.isValid(), True)
        s = sum(f.attributes()[0] for f in l4.getFeatures())
        self.assertEqual(s, 10659)

    def test_encoding(self):
        # changes encoding on a shapefile (the only provider supporting setEncoding)
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "shp_latin1.dbf"))
        l = QgsVectorLayer("?layer=ogr:%s:fp:latin1" % source, "vtab", "virtual", False)
        self.assertEqual(l.isValid(), True)

        for f in l.getFeatures():
            self.assertEqual(f.attributes()[1], u"accents éàè")

        # use UTF-8 now
        l = QgsVectorLayer("?layer=ogr:%s:fp:UTF-8" % source, "vtab", "virtual", False)
        self.assertEqual(l.isValid(), True)
        for f in l.getFeatures():
            self.assertEqual(f.attributes()[1], u"accents \ufffd\ufffd\ufffd") # invalid unicode characters

    def test_rowid(self):
        source = QUrl.toPercentEncoding(os.path.join(self.testDataDir, "france_parts.shp"))
        query = QUrl.toPercentEncoding("select rowid as uid, * from vtab limit 1 offset 3")
        l = QgsVectorLayer("?layer=ogr:%s:vtab&query=%s" % (source, query), "vtab2", "virtual", False)
        # the last line must have a fixed rowid (not an autoincrement)
        for f in l.getFeatures():
            lid = f.attributes()[0]
        self.assertEqual(lid, 3)

    def test_geometry_conversion(self):
        query = QUrl.toPercentEncoding("select geomfromtext('multipoint((0 0),(1 1))') as geom")
        l = QgsVectorLayer("?query=%s&geometry=geom:multipoint:0" % query, "tt", "virtual", False)
        self.assertEqual(l.isValid(), True)
        for f in l.getFeatures():
            self.assertEqual(f.geometry().exportToWkt().lower().startswith("multipoint"), True)
            self.assertEqual("),(" in f.geometry().exportToWkt(), True) # has two points

        query = QUrl.toPercentEncoding("select geomfromtext('multipolygon(((0 0,1 0,1 1,0 1,0 0)),((0 1,1 1,1 2,0 2,0 1)))') as geom")
        l = QgsVectorLayer("?query=%s&geometry=geom:multipolygon:0" % query, "tt", "virtual", False)
        self.assertEqual(l.isValid(), True)
        for f in l.getFeatures():
            self.assertEqual(f.geometry().exportToWkt().lower().startswith("multipolygon"), True)
            self.assertEqual(")),((" in f.geometry().exportToWkt(), True) # has two polygons

        query = QUrl.toPercentEncoding("select geomfromtext('multilinestring((0 0,1 0,1 1,0 1,0 0),(0 1,1 1,1 2,0 2,0 1))') as geom")
        l = QgsVectorLayer("?query=%s&geometry=geom:multilinestring:0" % query, "tt", "virtual", False)
        self.assertEqual(l.isValid(), True)
        for f in l.getFeatures():
            self.assertEqual(f.geometry().exportToWkt().lower().startswith("multilinestring"), True)
            self.assertEqual("),(" in f.geometry().exportToWkt(), True) # has two linestrings

    def test_queryOnMemoryLayer(self):
        ml = QgsVectorLayer("Point?srid=EPSG:4326&field=a:int", "mem", "memory")
        self.assertEqual(ml.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(ml)

        ml.startEditing()
        f1 = QgsFeature(ml.fields())
        f1.setGeometry(QgsGeometry.fromWkt('POINT(0 0)'))
        f2 = QgsFeature(ml.fields())
        f2.setGeometry(QgsGeometry.fromWkt('POINT(1 1)'))
        ml.addFeatures([f1, f2])
        ml.commitChanges()

        vl = QgsVectorLayer("?query=select * from mem", "vl", "virtual")
        self.assertEqual(vl.isValid(), True)

        self.assertEqual(ml.featureCount(), vl.featureCount())

        # test access to pending features as well
        ml.startEditing()
        f3 = QgsFeature(ml.fields())
        ml.addFeatures([f3])
        self.assertEqual(ml.featureCount(), vl.featureCount())

    def test_ProjectDependencies(self):
        # make a virtual layer with living references and save it to a project
        l1 = QgsVectorLayer(os.path.join(self.testDataDir, "france_parts.shp"), "france_parts", "ogr", False)
        self.assertEqual(l1.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l1)

        query = QUrl.toPercentEncoding("SELECT * FROM france_parts")
        l2 = QgsVectorLayer("?query=%s" % query, "aa", "virtual", False)
        self.assertEqual(l2.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l2)

        self.assertEqual(len(l2.layerDependencies()), 1)
        self.assertEqual(l2.layerDependencies()[0].startswith('france_parts'), True)

        query = QUrl.toPercentEncoding("SELECT t1.objectid, t2.name_0 FROM france_parts as t1, aa as t2")
        l3 = QgsVectorLayer("?query=%s" % query, "bb", "virtual", False)
        self.assertEqual(l3.isValid(), True)
        QgsMapLayerRegistry.instance().addMapLayer(l3)

        self.assertEqual(len(l2.layerDependencies()), 1)
        self.assertEqual(l2.layerDependencies()[0].startswith('france_parts'), True)

        self.assertEqual(len(l3.layerDependencies()), 2)

        temp = os.path.join(tempfile.gettempdir(), "qgstestproject.qgs")

        QgsProject.instance().setFileName(temp)
        QgsProject.instance().write()

        QgsMapLayerRegistry.instance().removeMapLayers([l1, l2])
        QgsProject.instance().clear()

        QgsProject.instance().setFileName(temp)
        QgsProject.instance().read()

        # make sure the 3 layers are loaded back
        self.assertEqual(len(QgsMapLayerRegistry.instance().mapLayers()), 3)

    def test_qgisExpressionFunctions(self):
        QgsProject.instance().setTitle('project')
        self.assertEqual(QgsProject.instance().title(), 'project')
        df = QgsVirtualLayerDefinition()
        df.setQuery("SELECT format('hello %1', 'world') as a, year(todate('2016-01-02')) as b, title('This') as t, var('project_title') as c")
        l = QgsVectorLayer(df.toString(), "testq", "virtual")
        self.assertEqual(l.isValid(), True)

        for f in l.getFeatures():
            self.assertEqual(f.attributes(), ['hello world', 2016, u'This', u'project'])


if __name__ == '__main__':
    unittest.main()
