// Copyright 2008 Nanorex, Inc.  See LICENSE file for details.

#include "OpenBabelImportExportTest.h"


CPPUNIT_TEST_SUITE_REGISTRATION(OpenBabelImportExportTest);
CPPUNIT_TEST_SUITE_NAMED_REGISTRATION(OpenBabelImportExportTest, "OpenBabelImportExportTestSuite");


/* FUNCTION: setUp */
void OpenBabelImportExportTest::setUp() {
	logger = new NXLogger();
	//logger->addHandler(new NXConsoleLogHandler(NXLogLevel_Info));
	entityManager = new NXEntityManager();
		
	NXProperties* properties = new NXProperties();
	properties->setProperty("PluginsSearchPath", "../lib");
	properties->setProperty("ImportExport.0.plugin",
							"OpenBabelImportExport");
	properties->setProperty("ImportExport.0.exportFormats",
							"Protein Data Bank (*.pdb)");
	properties->setProperty("ImportExport.0.importFormats",
							"Protein Data Bank (*.pdb)");
	entityManager->loadDataImportExportPlugins(properties);
	delete properties;
}


/* FUNCTION: tearDown */
void OpenBabelImportExportTest::tearDown() {
	delete entityManager;
	delete logger;
}


/* FUNCTION: basicExportTest */
void OpenBabelImportExportTest::basicExportTest() {

	// Create a water molecule for frame 0
	//
	int frameSetId = entityManager->addFrameSet();
	int frameIndex = entityManager->addFrame(frameSetId);
	NXMoleculeSet* rootMoleculeSet =
		entityManager->getRootMoleculeSet(frameSetId, frameIndex);
	OBMol* molecule = rootMoleculeSet->newMolecule();
	OBAtom* atomO = molecule->NewAtom();
	atomO->SetAtomicNum(etab.GetAtomicNum("O")); // Oxygen
	atomO->SetVector(0.00000000, 0.00000000, 0.37000000); // Angstroms
	OBAtom* atomH1 = molecule->NewAtom();
	atomH1->SetAtomicNum(etab.GetAtomicNum("H")); // Hydrogen
	atomH1->SetVector(0.78000000, 0.00000000, -0.18000000);
	OBAtom* atomH2 = molecule->NewAtom();
	atomH2->SetAtomicNum(etab.GetAtomicNum("H")); // Hydrogen
	atomH2->SetVector(-0.78000000, 0.00000000, -0.18000000);
	OBBond* bond = molecule->NewBond();
	bond->SetBegin(atomO);
	bond->SetEnd(atomH1);
	bond = molecule->NewBond();
	bond->SetBegin(atomO);
	bond->SetEnd(atomH2);
	
	// Write it with the OpenBabelImportExport plugin
	NXCommandResult* commandResult =
		entityManager->exportToFile("testOpenBabel.pdb", frameSetId, -1);
	if (commandResult->getResult() != NX_CMD_SUCCESS)
		printf("\n%s\n", qPrintable(GetNV1ResultCodeString(commandResult)));
	CPPUNIT_ASSERT(commandResult->getResult() == NX_CMD_SUCCESS);
}


/* FUNCTION: basicImportTest */
void OpenBabelImportExportTest::basicImportTest() {

	// Read with the OpenBabelImportExport plugin
	NXCommandResult* commandResult =
		entityManager->importFromFile("testOpenBabel.pdb");
	if (commandResult->getResult() != NX_CMD_SUCCESS)
		printf("\n%s\n", qPrintable(GetNV1ResultCodeString(commandResult)));
	CPPUNIT_ASSERT(commandResult->getResult() == NX_CMD_SUCCESS);
	
	NXMoleculeSet* rootMoleculeSet = entityManager->getRootMoleculeSet(0, 0);
	CPPUNIT_ASSERT(rootMoleculeSet != 0);
	OBMolIterator moleculeIter = rootMoleculeSet->moleculesBegin();
	CPPUNIT_ASSERT((*moleculeIter)->GetAtom(1)->GetAtomicNum() == 8);
	CPPUNIT_ASSERT_DOUBLES_EQUAL(0.37, (*moleculeIter)->GetAtom(1)->GetZ(),
								 0.001);
	CPPUNIT_ASSERT((*moleculeIter)->NumBonds() == 2);
}
